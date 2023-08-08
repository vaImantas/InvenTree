"""Django views for interacting with Part app."""

import os
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import HttpResponseRedirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from common.files import FileManager
from common.models import InvenTreeSetting
from common.views import FileManagementAjaxView, FileManagementFormView
from company.models import SupplierPart
from InvenTree.helpers import str2bool, str2int
from InvenTree.views import AjaxUpdateView, AjaxView, InvenTreeRoleMixin
from plugin.views import InvenTreePluginViewMixin
from stock.models import StockItem, StockLocation

from . import forms as part_forms
from . import settings as part_settings
from .bom import ExportBom, IsValidBOMFormat, MakeBomTemplate
from .models import Part, PartCategory
from .part import MakePartTemplate


class PartIndex(InvenTreeRoleMixin, InvenTreePluginViewMixin, ListView):
    """View for displaying list of Part objects."""

    model = Part
    template_name = 'part/category.html'
    context_object_name = 'parts'

    def get_queryset(self):
        """Custom queryset lookup to prefetch related fields"""
        return Part.objects.all().select_related('category')

    def get_context_data(self, **kwargs):
        """Returns custom context data for the PartIndex view:

        - children: Number of child categories
        - category_count: Number of child categories
        - part_count: Number of parts contained
        """
        context = super().get_context_data(**kwargs).copy()

        # View top-level categories
        children = PartCategory.objects.filter(parent=None)

        context['children'] = children
        context['category_count'] = PartCategory.objects.count()
        context['part_count'] = Part.objects.count()

        return context


class PartImport(FileManagementFormView):
    """Part: Upload file, match to fields and import parts(using multi-Step form)"""
    permission_required = 'part.add'

    class PartFileManager(FileManager):
        """Import field definitions"""
        REQUIRED_HEADERS = [
            'Name',
            'Description',
        ]

        OPTIONAL_MATCH_HEADERS = [
            'Category',
            'default_location',
            'default_supplier',
            'variant_of',
        ]

        OPTIONAL_HEADERS = [
            'Keywords',
            'IPN',
            'Revision',
            'Link',
            'default_expiry',
            'minimum_stock',
            'Units',
            'Notes',
            'Active',
            'base_cost',
            'Multiple',
            'Assembly',
            'Component',
            'is_template',
            'Purchasable',
            'Salable',
            'Trackable',
            'Virtual',
            'Stock',
            'Image',
        ]

    name = 'part'
    form_steps_template = [
        'part/import_wizard/part_upload.html',
        'part/import_wizard/match_fields.html',
        'part/import_wizard/match_references.html',
    ]
    form_steps_description = [
        _("Upload File"),
        _("Match Fields"),
        _("Match References"),
    ]

    form_field_map = {
        'name': 'name',
        'description': 'description',
        'keywords': 'keywords',
        'ipn': 'ipn',
        'revision': 'revision',
        'link': 'link',
        'default_expiry': 'default_expiry',
        'minimum_stock': 'minimum_stock',
        'units': 'units',
        'notes': 'notes',
        'category': 'category',
        'default_location': 'default_location',
        'default_supplier': 'default_supplier',
        'variant_of': 'variant_of',
        'active': 'active',
        'base_cost': 'base_cost',
        'multiple': 'multiple',
        'assembly': 'assembly',
        'component': 'component',
        'is_template': 'is_template',
        'purchaseable': 'purchaseable',
        'salable': 'salable',
        'trackable': 'trackable',
        'virtual': 'virtual',
        'stock': 'stock',
        'image': 'image',
    }
    file_manager_class = PartFileManager

    def get_field_selection(self):
        """Fill the form fields for step 3."""
        # fetch available elements
        self.allowed_items = {}
        self.matches = {}

        self.allowed_items['Category'] = PartCategory.objects.all().exclude(structural=True)
        self.matches['Category'] = ['name__icontains']
        self.allowed_items['default_location'] = StockLocation.objects.all().exclude(structural=True)
        self.matches['default_location'] = ['name__icontains']
        self.allowed_items['default_supplier'] = SupplierPart.objects.all()
        self.matches['default_supplier'] = ['SKU__icontains']
        self.allowed_items['variant_of'] = Part.objects.all().exclude(is_template=False)
        self.matches['variant_of'] = ['name__icontains']

        # setup
        self.file_manager.setup()
        # collect submitted column indexes
        col_ids = {}
        for col in self.file_manager.HEADERS:
            index = self.get_column_index(col)
            if index >= 0:
                col_ids[col] = index

        # parse all rows
        for row in self.rows:
            # check each submitted column
            for idx in col_ids:
                data = row['data'][col_ids[idx]]['cell']

                if idx in self.file_manager.OPTIONAL_MATCH_HEADERS:
                    try:
                        exact_match = self.allowed_items[idx].get(**{a: data for a in self.matches[idx]})
                    except (ValueError, self.allowed_items[idx].model.DoesNotExist, self.allowed_items[idx].model.MultipleObjectsReturned):
                        exact_match = None

                    row['match_options_' + idx] = self.allowed_items[idx]
                    row['match_' + idx] = exact_match
                    continue

                # general fields
                row[idx.lower()] = data

    def done(self, form_list, **kwargs):
        """Create items."""
        items = self.get_clean_items()

        import_done = 0
        import_error = []

        # Create Part instances
        for part_data in items.values():

            # set related parts
            optional_matches = {}
            for idx in self.file_manager.OPTIONAL_MATCH_HEADERS:
                if idx.lower() in part_data:
                    try:
                        optional_matches[idx] = self.allowed_items[idx].get(pk=int(part_data[idx.lower()]))
                    except (ValueError, self.allowed_items[idx].model.DoesNotExist, self.allowed_items[idx].model.MultipleObjectsReturned):
                        optional_matches[idx] = None
                else:
                    optional_matches[idx] = None

            # add part
            new_part = Part(
                name=part_data.get('name', ''),
                description=part_data.get('description', ''),
                keywords=part_data.get('keywords', None),
                IPN=part_data.get('ipn', None),
                revision=part_data.get('revision', None),
                link=part_data.get('link', None),
                default_expiry=str2int(part_data.get('default_expiry'), 0),
                minimum_stock=str2int(part_data.get('minimum_stock'), 0),
                units=part_data.get('units', None),
                notes=part_data.get('notes', None),
                category=optional_matches['Category'],
                default_location=optional_matches['default_location'],
                default_supplier=optional_matches['default_supplier'],
                variant_of=optional_matches['variant_of'],
                active=str2bool(part_data.get('active', True)),
                base_cost=str2int(part_data.get('base_cost'), 0),
                multiple=str2int(part_data.get('multiple'), 1),
                assembly=str2bool(part_data.get('assembly', part_settings.part_assembly_default())),
                component=str2bool(part_data.get('component', part_settings.part_component_default())),
                is_template=str2bool(part_data.get('is_template', part_settings.part_template_default())),
                purchaseable=str2bool(part_data.get('purchaseable', part_settings.part_purchaseable_default())),
                salable=str2bool(part_data.get('salable', part_settings.part_salable_default())),
                trackable=str2bool(part_data.get('trackable', part_settings.part_trackable_default())),
                virtual=str2bool(part_data.get('virtual', part_settings.part_virtual_default())),
                image=part_data.get('image', None),
            )

            # check if there's a category assigned, if not skip this part or else bad things happen
            if not optional_matches['Category']:
                import_error.append(_("Can't import part {name} because there is no category assigned").format(name=new_part.name))
                continue

            try:
                new_part.save()

                # add stock item if set
                if part_data.get('stock', None):
                    stock = StockItem(
                        part=new_part,
                        location=new_part.default_location,
                        quantity=int(part_data.get('stock', 1)),
                    )
                    stock.save()

                import_done += 1
            except ValidationError as _e:
                import_error.append(', '.join(set(_e.messages)))

        # Set alerts
        if import_done:
            alert = f"<strong>{_('Part-Import')}</strong><br>{_('Imported {n} parts').format(n=import_done)}"
            messages.success(self.request, alert)
        if import_error:
            error_text = '\n'.join([f'<li><strong>{import_error.count(a)}</strong>: {a}</li>' for a in set(import_error)])
            messages.error(self.request, f"<strong>{_('Some errors occurred:')}</strong><br><ul>{error_text}</ul>")

        return HttpResponseRedirect(reverse('part-index'))


class PartImportTemplate(AjaxView):
    """Provide a part import template file for download.

    - Generates a template file in the provided format e.g. ?format=csv
    """

    def get(self, request, *args, **kwargs):
        """Perform a GET request to download the 'Part import' template"""
        export_format = request.GET.get('format', 'csv')

        return MakePartTemplate(export_format)


class PartImportAjax(FileManagementAjaxView, PartImport):
    """Multi-step form wizard for importing Part data"""
    ajax_form_steps_template = [
        'part/import_wizard/ajax_part_upload.html',
        'part/import_wizard/ajax_match_fields.html',
        'part/import_wizard/ajax_match_references.html',
    ]

    def validate(self, obj, form, **kwargs):
        """Validation is performed based on the current form step"""
        return PartImport.validate(self, self.steps.current, form, **kwargs)


class PartDetail(InvenTreeRoleMixin, InvenTreePluginViewMixin, DetailView):
    """Detail view for Part object."""

    context_object_name = 'part'
    queryset = Part.objects.all().select_related('category')
    template_name = 'part/detail.html'
    form_class = part_forms.PartPriceForm

    # Add in some extra context information based on query params
    def get_context_data(self, **kwargs):
        """Provide extra context data to template."""
        context = super().get_context_data(**kwargs)

        part = self.get_object()

        ctx = part.get_context_data(self.request)

        context.update(**ctx)

        return context

    def get_quantity(self):
        """Return set quantity in decimal format."""
        return Decimal(self.request.POST.get('quantity', 1))

    def get_part(self):
        """Return the Part instance associated with this view"""
        return self.get_object()

    def get_initials(self):
        """Returns initials for form."""
        return {'quantity': self.get_quantity()}

    def post(self, request, *args, **kwargs):
        """POST action performs as a GET action"""
        self.object = self.get_object()
        kwargs['object'] = self.object
        ctx = self.get_context_data(**kwargs)
        return self.get(request, context=ctx)


class PartDetailFromIPN(PartDetail):
    """Part detail view using the IPN (internal part number) of the Part as the lookup field"""

    slug_field = 'IPN'
    slug_url_kwarg = 'slug'

    def get_object(self):
        """Return Part object which IPN field matches the slug value."""
        queryset = self.get_queryset()
        # Get slug
        slug = self.kwargs.get(self.slug_url_kwarg)

        if slug is not None:
            slug_field = self.get_slug_field()
            # Filter by the slug value
            queryset = queryset.filter(**{slug_field: slug})

            try:
                # Get unique part from queryset
                part = queryset.get()
                # Return Part object
                return part
            except queryset.model.MultipleObjectsReturned:
                pass
            except queryset.model.DoesNotExist:
                pass

        return None

    def get(self, request, *args, **kwargs):
        """Attempt to match slug to a Part, else redirect to PartIndex view."""
        self.object = self.get_object()

        if not self.object:
            return HttpResponseRedirect(reverse('part-index'))

        return super(PartDetailFromIPN, self).get(request, *args, **kwargs)


class PartImageSelect(AjaxUpdateView):
    """View for selecting Part image from existing images."""

    model = Part
    ajax_template_name = 'part/select_image.html'
    ajax_form_title = _('Select Part Image')

    fields = [
        'image',
    ]

    def post(self, request, *args, **kwargs):
        """Perform POST action to assign selected image to the Part instance"""
        part = self.get_object()
        form = self.get_form()

        img = request.POST.get('image', '')

        img = os.path.basename(img)

        data = {}

        if img:
            img_path = settings.MEDIA_ROOT.joinpath('part_images', img)

            # Ensure that the image already exists
            if os.path.exists(img_path):

                part.image = os.path.join('part_images', img)
                part.save()

                data['success'] = _('Updated part image')

        if 'success' not in data:
            data['error'] = _('Part image not found')

        return self.renderJsonResponse(request, form, data)


class BomUpload(InvenTreeRoleMixin, DetailView):
    """View for uploading a BOM file, and handling BOM data importing."""

    context_object_name = 'part'
    queryset = Part.objects.all()
    template_name = 'part/upload_bom.html'


class BomUploadTemplate(AjaxView):
    """Provide a BOM upload template file for download.

    - Generates a template file in the provided format e.g. ?format=csv
    """

    def get(self, request, *args, **kwargs):
        """Perform a GET request to download the 'BOM upload' template"""
        export_format = request.GET.get('format', 'csv')

        return MakeBomTemplate(export_format)


class BomDownload(AjaxView):
    """Provide raw download of a BOM file.

    - File format should be passed as a query param e.g. ?format=csv
    """

    role_required = 'part.view'

    model = Part

    def get(self, request, *args, **kwargs):
        """Perform GET request to download BOM data"""
        part = get_object_or_404(Part, pk=self.kwargs['pk'])

        export_format = request.GET.get('format', 'csv')

        cascade = str2bool(request.GET.get('cascade', False))

        parameter_data = str2bool(request.GET.get('parameter_data', False))

        substitute_part_data = str2bool(request.GET.get('substitute_part_data', False))

        stock_data = str2bool(request.GET.get('stock_data', False))

        supplier_data = str2bool(request.GET.get('supplier_data', False))

        manufacturer_data = str2bool(request.GET.get('manufacturer_data', False))

        pricing_data = str2bool(request.GET.get('pricing_data', False))

        levels = request.GET.get('levels', None)

        if levels is not None:
            try:
                levels = int(levels)

                if levels <= 0:
                    levels = None

            except ValueError:
                levels = None

        if not IsValidBOMFormat(export_format):
            export_format = 'csv'

        return ExportBom(part,
                         fmt=export_format,
                         cascade=cascade,
                         max_levels=levels,
                         parameter_data=parameter_data,
                         stock_data=stock_data,
                         supplier_data=supplier_data,
                         manufacturer_data=manufacturer_data,
                         pricing_data=pricing_data,
                         substitute_part_data=substitute_part_data,
                         )

    def get_data(self):
        """Return a custom message"""
        return {
            'info': 'Exported BOM'
        }


class PartPricing(AjaxView):
    """View for inspecting part pricing information."""

    model = Part
    ajax_template_name = "part/part_pricing.html"
    ajax_form_title = _("Part Pricing")
    form_class = part_forms.PartPriceForm

    role_required = ['sales_order.view', 'part.view']

    def get_quantity(self):
        """Return set quantity in decimal format."""
        return Decimal(self.request.POST.get('quantity', 1))

    def get_part(self):
        """Return the Part instance associated with this view"""
        try:
            return Part.objects.get(id=self.kwargs['pk'])
        except Part.DoesNotExist:
            return None

    def get_pricing(self, quantity=1, currency=None):
        """Returns context with pricing information."""
        if quantity <= 0:
            quantity = 1

        # TODO - Capacity for price comparison in different currencies
        currency = None

        # Currency scaler
        scaler = Decimal(1.0)

        part = self.get_part()

        ctx = {
            'part': part,
            'quantity': quantity,
            'currency': currency,
        }

        if part is None:
            return ctx

        # Supplier pricing information
        if part.supplier_count > 0:
            buy_price = part.get_supplier_price_range(quantity)

            if buy_price is not None:
                min_buy_price, max_buy_price = buy_price

                min_buy_price /= scaler
                max_buy_price /= scaler

                min_unit_buy_price = round(min_buy_price / quantity, 3)
                max_unit_buy_price = round(max_buy_price / quantity, 3)

                min_buy_price = round(min_buy_price, 3)
                max_buy_price = round(max_buy_price, 3)

                if min_buy_price:
                    ctx['min_total_buy_price'] = min_buy_price
                    ctx['min_unit_buy_price'] = min_unit_buy_price

                if max_buy_price:
                    ctx['max_total_buy_price'] = max_buy_price
                    ctx['max_unit_buy_price'] = max_unit_buy_price

        # BOM pricing information
        if part.bom_count > 0:

            use_internal = InvenTreeSetting.get_setting('PART_BOM_USE_INTERNAL_PRICE', False)
            bom_price = part.get_bom_price_range(quantity, internal=use_internal)
            purchase_price = part.get_bom_price_range(quantity, purchase=True)

            if bom_price is not None:
                min_bom_price, max_bom_price = bom_price

                min_bom_price /= scaler
                max_bom_price /= scaler

                if min_bom_price:
                    ctx['min_total_bom_price'] = round(min_bom_price, 3)
                    ctx['min_unit_bom_price'] = round(min_bom_price / quantity, 3)

                if max_bom_price:
                    ctx['max_total_bom_price'] = round(max_bom_price, 3)
                    ctx['max_unit_bom_price'] = round(max_bom_price / quantity, 3)

            if purchase_price is not None:
                min_bom_purchase_price, max_bom_purchase_price = purchase_price

                min_bom_purchase_price /= scaler
                max_bom_purchase_price /= scaler
                if min_bom_purchase_price:
                    ctx['min_total_bom_purchase_price'] = round(min_bom_purchase_price, 3)
                    ctx['min_unit_bom_purchase_price'] = round(min_bom_purchase_price / quantity, 3)

                if max_bom_purchase_price:
                    ctx['max_total_bom_purchase_price'] = round(max_bom_purchase_price, 3)
                    ctx['max_unit_bom_purchase_price'] = round(max_bom_purchase_price / quantity, 3)

        # internal part pricing information
        internal_part_price = part.get_internal_price(quantity)
        if internal_part_price is not None:
            ctx['total_internal_part_price'] = round(internal_part_price, 3)
            ctx['unit_internal_part_price'] = round(internal_part_price / quantity, 3)

        # part pricing information
        part_price = part.get_price(quantity)
        if part_price is not None:
            ctx['total_part_price'] = round(part_price, 3)
            ctx['unit_part_price'] = round(part_price / quantity, 3)

        return ctx

    def get_initials(self):
        """Returns initials for form."""
        return {'quantity': self.get_quantity()}

    def get(self, request, *args, **kwargs):
        """Perform custom GET action for this view"""
        init = self.get_initials()
        qty = self.get_quantity()

        return self.renderJsonResponse(request, self.form_class(initial=init), context=self.get_pricing(qty))

    def post(self, request, *args, **kwargs):
        """Perform custom POST action for this view"""
        currency = None

        quantity = self.get_quantity()

        # Retain quantity value set by user
        form = self.form_class(initial=self.get_initials())

        # TODO - How to handle pricing in different currencies?
        currency = None

        # check if data is set
        try:
            data = self.data
        except AttributeError:
            data = {}

        # Always mark the form as 'invalid' (the user may wish to keep getting pricing data)
        data['form_valid'] = False

        return self.renderJsonResponse(request, form, data=data, context=self.get_pricing(quantity, currency))


class CategoryDetail(InvenTreeRoleMixin, InvenTreePluginViewMixin, DetailView):
    """Detail view for PartCategory."""

    model = PartCategory
    context_object_name = 'category'
    queryset = PartCategory.objects.all().prefetch_related('children')
    template_name = 'part/category.html'

    def get_context_data(self, **kwargs):
        """Returns custom context data for the CategoryDetail view:

        - part_count: Number of parts in this category
        - starred_directly: True if this category is starred directly by the requesting user
        - starred: True if this category is starred by the requesting user
        """
        context = super().get_context_data(**kwargs).copy()

        try:
            context['part_count'] = kwargs['object'].partcount()
        except KeyError:
            context['part_count'] = 0

        # Get current category
        category = kwargs.get('object', None)

        if category:

            # Insert "starred" information
            context['starred_directly'] = category.is_starred_by(
                self.request.user,
                include_parents=False,
            )

            if context['starred_directly']:
                # Save a database lookup - if 'starred_directly' is True, we know 'starred' is also
                context['starred'] = True
            else:
                context['starred'] = category.is_starred_by(self.request.user)

        return context
