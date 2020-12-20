odoo.define('report_xml.report', function (require) {
    'use strict';

    var ActionManager = require('web.ActionManager');
    var core = require('web.core');
    var framework = require('web.framework');
    var session = require('web.session');
    var _t = core._t;

    ActionManager.include({

        _executeReportAction: function (action, options) {
            var self = this;
            if (action.report_type === 'jasper') {
                return self._triggerDownload(action, options, 'jasper');
            }
            return this._super.apply(this, arguments);
        },

        _downloadReportJasper: function (url) {
            var self = this;
            framework.blockUI();
            return new Promise(function (resolve, reject) {
                var reporttype = url.split('/')[2];
                var type = 'jasper';
                var blocked = !session.get_file({
                    url: '/report/download',
                    data: {
                        data: JSON.stringify([url, type]),
                        context: JSON.stringify(session.user_context),
                    },
                    success: resolve,
                    error: (error) => {
                        self.call('crash_manager', 'rpc_error', error);
                        reject();
                    },
                    complete: framework.unblockUI,
                });
                if (blocked) {
                    // AAB: this check should be done in get_file service directly,
                    // should not be the concern of the caller (and that way, get_file
                    // could return a promise)
                    var message = _t('A popup window with your report was blocked. You ' +
                                     'may need to change your browser settings to allow ' +
                                     'popup windows for this page.');
                    self.do_warn(_t('Warning'), message, true);
                }
            });
        },

        _makeReportUrlsJasper: function (action) {
            var reportUrls = this._makeReportUrls(action);
            reportUrls.jasper = '/report/jasper/' + action.report_name;

            // We may have to build a query string with `action.data`. It's the place
            // were report's using a wizard to customize the output traditionally put
            // their options.
            if (_.isUndefined(action.data) || _.isNull(action.data) ||
                (_.isObject(action.data) && _.isEmpty(action.data))) {
                if (action.context.active_ids) {
                    var activeIDsPath = '/' + action.context.active_ids.join(',');
                    reportUrls = _.mapObject(reportUrls, function (value) {
                        return value += activeIDsPath;
                    });
                }
                reportUrls.html += '?context=' + encodeURIComponent(JSON.stringify(session.user_context));
            } else {
                var serializedOptionsPath = '?options=' + encodeURIComponent(JSON.stringify(action.data));
                serializedOptionsPath += '&context=' + encodeURIComponent(JSON.stringify(action.context));
                reportUrls = _.mapObject(reportUrls, function (value) {
                    return value += serializedOptionsPath;
                });
            }
            return reportUrls;
        },
    
            _triggerDownload: function (action, options, type) {
            if (type === "jasper") {
                var self = this;
                var reportUrls = this._makeReportUrlsJasper(action);
                return this._downloadReportJasper(
                    reportUrls[type]).then(function () {
                    if (action.close_on_report_download) {
                        var closeAction = { 
                            type: 'ir.actions.act_window_close' 
                        };
                        return self.doAction(
                            closeAction, _.pick(options, 'on_close'));
                    } else {
                        return options.on_close();
                    }
                }
                );
            }
            return this._super.apply(this, arguments);
    
        },

    });
});
