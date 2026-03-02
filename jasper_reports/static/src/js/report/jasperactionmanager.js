/** @odoo-module */

import {download} from "@web/core/network/download";
import {registry} from "@web/core/registry";

function getJasperReportUrl(action, userContext) {
    const type = action.report_type;
    let url = `/report/${type}/${action.report_name}`;
    const actionContext = action.context || {};

    if (action.data && JSON.stringify(action.data) !== "{}") {
        // Build a query string with `action.data` (wizard/custom report options).
        const options = encodeURIComponent(JSON.stringify(action.data));
        const context = encodeURIComponent(JSON.stringify(actionContext));
        url += `?options=${options}&context=${context}`;
    } else {
        if (actionContext.active_ids) {
            url += `/${actionContext.active_ids.join(",")}`;
        }
        if (type === "jasper") {
            const context = encodeURIComponent(JSON.stringify(userContext));
            url += `?context=${context}`;
        }
    }

    return url;
}

registry
    .category("ir.actions.report handlers")
    .add("jasper_handler", async (action, options, env) => {
        if (action.report_type !== "jasper") {
            return false;
        }

        const {ui, user, action: actionService} = env.services;
        const url = getJasperReportUrl(action, user.context);

        ui.block();
        try {
            console.log("Downloading report from URL:", url);
            await download({
                url: "/report/download",
                data: {
                    data: JSON.stringify([url, action.report_type]),
                    context: JSON.stringify(user.context),
                },
            });
            console.log("Downloading report from URL:");
        } finally {
            ui.unblock();
        }

        const onClose = options?.onClose;
        if (action.close_on_report_download) {
            return actionService.doAction(
                {type: "ir.actions.act_window_close"},
                {onClose}
            );
        }
        if (onClose) {
            onClose();
        }
        return true;
    });
