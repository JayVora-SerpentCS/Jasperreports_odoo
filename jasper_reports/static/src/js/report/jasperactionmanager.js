odoo.define('report_xml.report', function(require) {
    'use strict';

    var ActionManager = require('web.ActionManager');
    var crash_manager = require('web.crash_manager');
    var framework = require('web.framework');

    ActionManager.include({
        ir_actions_report: function(action, options) {
            var self = this;
            var parameters = '';
            if(action.data){
                var parameters = action.data.parameters
            }
            var cloned_action = _.clone(action);
            if (cloned_action.report_type === 'jasper') {
                framework.blockUI();
                var report_jasper_url = 'report/jasper/' + cloned_action.report_name;
                if (cloned_action.context.active_ids) {
                    report_jasper_url += '/' + cloned_action.context.active_ids.join(',');
                } else {
                    report_jasper_url += '?options=' + encodeURIComponent(JSON.stringify(cloned_action.data));
                    report_jasper_url += '&context=' + encodeURIComponent(JSON.stringify(cloned_action.context));
                }
                self.getSession().get_file({
                    url: report_jasper_url,
                    data: {
                        parameters: JSON.stringify(parameters),
                        data: JSON.stringify([
                            report_jasper_url,
                            cloned_action.report_type,
                        ])
                    },
                    error: crash_manager.rpc_error.bind(crash_manager),
                    success: function() {
                        if (cloned_action && options && !cloned_action.dialog) {
                            options.on_close();
                        }
                    }
                });
                framework.unblockUI();
                return;
            }
            return self._super(action, options);
        }
    });
});
