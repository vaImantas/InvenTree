{% load i18n %}


/* globals
    inventreeGet,
    inventreePut,
    renderLink,
    setupFilterList,
*/


/* exported
    loadNotificationTable,
    startNotificationWatcher,
    stopNotificationWatcher,
    openNotificationPanel,
    closeNotificationPanel,
*/


/*
 * Load notification table
 */
function loadNotificationTable(table, options={}, enableDelete=false) {

    var params = options.params || {};
    var read = typeof(params.read) === 'undefined' ? true : params.read;

    setupFilterList(`notifications-${options.name}`, $(table));

    $(table).inventreeTable({
        url: options.url,
        name: options.name,
        groupBy: false,
        search: true,
        queryParams: {
            ordering: 'age',
            read: read,
        },
        paginationVAlign: 'bottom',
        formatNoMatches: options.no_matches,
        columns: [
            {
                field: 'pk',
                title: '{% trans "ID" %}',
                visible: false,
                switchable: false,
            },
            {
                field: 'age',
                title: '{% trans "Age" %}',
                sortable: 'true',
                formatter: function(value, row) {
                    return row.age_human;
                }
            },
            {
                field: 'category',
                title: '{% trans "Category" %}',
                sortable: 'true',
            },
            {
                field: 'name',
                title: '{% trans "Notification" %}',
                formatter: function(value, row) {
                    if (row.target && row.target.link) {
                        return renderLink(value, row.target.link);
                    } else {
                        return value;
                    }
                }
            },
            {
                field: 'message',
                title: '{% trans "Message" %}',
            },
            {
                formatter: function(value, row, index, field) {
                    var bRead = getReadEditButton(row.pk, row.read);

                    let bDel = '';

                    if (enableDelete) {
                        bDel = `<button title='{% trans "Delete Notification" %}' class='notification-delete btn btn-outline-secondary' type='button' pk='${row.pk}'><span class='fas fa-trash-alt icon-red'></span></button>`;
                    }

                    var html = `<div class='btn-group float-right' role='group'>${bRead}${bDel}</div>`;

                    return html;
                }
            }
        ]
    });

    $(table).on('click', '.notification-read', function() {
        updateNotificationReadState($(this));
    });
}


var notificationWatcher = null; // reference for the notificationWatcher

/**
 * start the regular notification checks
 **/
function startNotificationWatcher() {
    notificationCheck(true);
    notificationWatcher = setInterval(notificationCheck, 5000);
}

/**
 * stop the regular notification checks
 **/
function stopNotificationWatcher() {
    clearInterval(notificationWatcher);
}


var notificationUpdateTic = 0;
/**
 * The notification checker is initiated when the document is loaded. It checks if there are unread notifications
 * if unread messages exist the notification indicator is updated
 *
 * options:
 * - force: set true to force an update now (if you got in focus for example)
 **/
function notificationCheck(force = false) {
    notificationUpdateTic = notificationUpdateTic + 1;

    // refresh if forced or
    // if in focus and was not refreshed in the last 5 seconds
    if (force || (document.hasFocus() && notificationUpdateTic >= 5)) {
        notificationUpdateTic = 0;
        inventreeGet(
            '/api/notifications/',
            {
                read: false,
            },
            {
                success: function(response) {
                    updateNotificationIndicator(response.length);
                },
                error: function(xhr) {
                    console.warn('Could not access server: /api/notifications');
                }
            }
        );
    }
}

/**
 * handles read / unread buttons and UI rebuilding
 *
 * arguments:
 * - btn: element that got clicked / fired the event -> must contain pk and target as attributes
 *
 * options:
 * - panel_caller: this button was clicked in the notification panel
 **/
function updateNotificationReadState(btn, panel_caller=false) {

    // Determine 'read' status of the notification
    var status = btn.attr('target') == 'read';
    var pk = btn.attr('pk');

    var url = `/api/notifications/${pk}/`;

    inventreePut(
        url,
        {
            read: status,
        },
        {
            method: 'PATCH',
            success: function() {
                // update the notification tables if they were declared
                if (window.updateNotifications) {
                    window.updateNotifications();
                }

                // update current notification count
                var count = parseInt($('#notification-counter').html());

                if (status) {
                    count = count - 1;
                } else {
                    count = count + 1;
                }

                // Prevent negative notification count
                if (count < 0) {
                    count = 0;
                }

                // update notification indicator now
                updateNotificationIndicator(count);

                // remove notification if called from notification panel
                if (panel_caller) {
                    btn.parent().parent().remove();
                }
            }
        }
    );
}


/**
 * Returns the html for a read / unread button
 *
 * arguments:
 * - pk: primary key of the notification
 * - state: current state of the notification (read / unread) -> just pass what you were handed by the api
 * - small: should the button be small
 **/
function getReadEditButton(pk, state, small=false) {

    let bReadText = '';
    let bReadIcon = '';
    let bReadTarget = '';

    if (state) {
        bReadText = '{% trans "Mark as unread" %}';
        bReadIcon = 'fas fa-bookmark icon-red';
        bReadTarget = 'unread';
    } else {
        bReadText = '{% trans "Mark as read" %}';
        bReadIcon = 'far fa-bookmark icon-green';
        bReadTarget = 'read';
    }

    let style = (small) ? 'btn-sm ' : '';

    return `<button title='${bReadText}' class='notification-read btn ${style}btn-outline-secondary float-right' type='button' pk='${pk}' target='${bReadTarget}'><span class='${bReadIcon}'></span></button>`;
}

/**
 * fills the notification panel when opened
 **/
function openNotificationPanel() {
    var html = '';
    var center_ref = '#notification-center';

    inventreeGet(
        '/api/notifications/',
        {
            read: false,
            ordering: '-creation',
        },
        {
            success: function(response) {
                if (response.length == 0) {
                    html = `<p class='text-muted'><em>{% trans "No unread notifications" %}</em><span class='fas fa-check-circle icon-green float-right'></span></p>`;
                } else {
                    // build up items
                    response.forEach(function(item, index) {
                        html += '<li class="list-group-item">';
                        html += `<div>`;
                        html += `<span class="badge bg-secondary rounded-pill">${item.name}</span>`;
                        html += getReadEditButton(item.pk, item.read, true);
                        html += `</div>`;

                        if (item.target) {
                            var link_text = `${item.target.name}`;
                            if (item.target.link) {
                                link_text = `<a href='${item.target.link}'>${link_text}</a>`;
                            }
                            html += link_text;
                        }

                        html += '<div>';
                        html += `<span class="text-muted"><small>${item.age_human}</small></span>`;
                        html += '</div></li>';
                    });

                    // package up
                    html = `<ul class="list-group">${html}</ul>`;
                }

                // set html
                $(center_ref).html(html);
            }
        }
    );

    $(center_ref).on('click', '.notification-read', function() {
        updateNotificationReadState($(this), true);
    });
}

/**
 * clears the notification panel when closed
 **/
function closeNotificationPanel() {
    $('#notification-center').html(`<p class='text-muted'>{% trans "Notifications will load here" %}</p>`);
}

/**
 * updates the notification counter
 **/
function updateNotificationIndicator(count) {
    // reset update Ticker -> safe some API bandwidth
    notificationUpdateTic = 0;

    if (count == 0) {
        $('#notification-alert').addClass('d-none');
    } else {
        $('#notification-alert').removeClass('d-none');
    }
    $('#notification-counter').html(count);
}
