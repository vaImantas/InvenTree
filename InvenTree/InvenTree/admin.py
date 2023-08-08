"""Admin classes"""

from import_export.resources import ModelResource


class InvenTreeResource(ModelResource):
    """Custom subclass of the ModelResource class provided by django-import-export"

    Ensures that exported data are escaped to prevent malicious formula injection.
    Ref: https://owasp.org/www-community/attacks/CSV_Injection
    """

    def export_resource(self, obj):
        """Custom function to override default row export behaviour.

        Specifically, strip illegal leading characters to prevent formula injection
        """
        row = super().export_resource(obj)

        illegal_start_vals = ['@', '=', '+', '-', '@', '\t', '\r', '\n']

        for idx, val in enumerate(row):
            if type(val) is str:
                val = val.strip()

                # If the value starts with certain 'suspicious' values, remove it!
                while len(val) > 0 and val[0] in illegal_start_vals:
                    # Remove the first character
                    val = val[1:]

                row[idx] = val

        return row

    def get_fields(self, **kwargs):
        """Return fields, with some common exclusions"""

        fields = super().get_fields(**kwargs)

        fields_to_exclude = [
            'metadata',
            'lft', 'rght', 'tree_id', 'level',
        ]

        return [f for f in fields if f.column_name not in fields_to_exclude]
