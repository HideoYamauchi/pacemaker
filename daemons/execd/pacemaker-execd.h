/*
 * Copyright 2012-2025 the Pacemaker project contributors
 *
 * The version control history for this file may have further details.
 *
 * This source code is licensed under the GNU Lesser General Public License
 * version 2.1 or later (LGPLv2.1+) WITHOUT ANY WARRANTY.
 */

#ifndef PACEMAKER_EXECD__H
#  define PACEMAKER_EXECD__H

#  include <glib.h>
#  include <crm/common/ipc_internal.h>
#  include <crm/lrmd.h>
#  include <crm/stonith-ng.h>

#  include <gnutls/gnutls.h>

extern GHashTable *rsc_list;
extern time_t start_time;

extern struct qb_ipcs_service_handlers lrmd_ipc_callbacks;

typedef struct lrmd_rsc_s {
    char *rsc_id;
    char *class;
    char *provider;
    char *type;

    int call_opts;

    /* NEVER dereference this pointer,
     * It simply exists as a switch to let us know
     * when the currently active operation has completed */
    void *active;

    /* Operations in this list
     * have not been executed yet. */
    GList *pending_ops;
    /* Operations in this list are recurring operations
     * that have been handed off from the pending ops list. */
    GList *recurring_ops;

    /* If this resource is a fence device, probes are handled internally by the
     * executor, and this value indicates the result that should currently be
     * returned for probes. It should be one of:
     * PCMK_EXEC_DONE (to indicate "running"),
     * PCMK_EXEC_NO_FENCE_DEVICE ("not running"), or
     * PCMK_EXEC_NOT_CONNECTED ("unknown because fencer connection was lost").
     */
    pcmk__action_result_t fence_probe_result;

    crm_trigger_t *work;
} lrmd_rsc_t;

// in remoted_tls.c
int lrmd_init_remote_tls_server(void);
void execd_stop_tls_server(void);

int lrmd_server_send_reply(pcmk__client_t *client, uint32_t id, xmlNode *reply);

int lrmd_server_send_notify(pcmk__client_t *client, xmlNode *msg);

void notify_of_new_client(pcmk__client_t *new_client);

void free_rsc(gpointer data);

void handle_shutdown_ack(void);

void handle_shutdown_nack(void);

void lrmd_client_destroy(pcmk__client_t *client);

void client_disconnect_cleanup(const char *client_id);

/*!
 * \brief Don't worry about freeing this connection. It is
 *        taken care of after mainloop exits by the main() function.
 */
stonith_t *get_stonith_connection(void);

/*!
 * \brief This is a callback that tells the lrmd
 * the current stonith connection has gone away. This allows
 * us to timeout any pending stonith commands
 */
void stonith_connection_failed(void);

#ifdef PCMK__COMPILE_REMOTE
void ipc_proxy_init(void);
void ipc_proxy_cleanup(void);
void ipc_proxy_add_provider(pcmk__client_t *client);
void ipc_proxy_remove_provider(pcmk__client_t *client);
void ipc_proxy_forward_client(pcmk__client_t *client, xmlNode *xml);
pcmk__client_t *ipc_proxy_get_provider(void);
int ipc_proxy_shutdown_req(pcmk__client_t *ipc_proxy);
void remoted_spawn_pidone(int argc, char **argv);
void remoted_request_cib_schema_files(void);
#endif

void execd_unregister_handlers(void);

void lrmd_drain_alerts(GMainLoop *mloop);

void execd_process_message(pcmk__client_t *c, uint32_t id, uint32_t flags,
                          xmlNode *msg);

xmlNode *execd_create_reply_as(const char *origin, int rc, int call_id);
void execd_send_generic_notify(int rc, xmlNode *request);

#define execd_create_reply(rc, call_id) \
    execd_create_reply_as(__func__, (rc), (call_id))

int execd_process_alert_exec(pcmk__client_t *client, xmlNode *request);
int execd_process_get_recurring(xmlNode *request, int call_id, xmlNode **reply);
int execd_process_get_rsc_info(xmlNode *request, int call_id, xmlNode **reply);
int execd_process_rsc_cancel(pcmk__client_t *client, xmlNode *request);
int execd_process_rsc_exec(pcmk__client_t *client, xmlNode *request);
void execd_process_rsc_register(pcmk__client_t *client, uint32_t id, xmlNode *request);
int execd_process_rsc_unregister(pcmk__client_t *client, xmlNode *request);
int execd_process_signon(pcmk__client_t *client, xmlNode *request, int call_id,
                         xmlNode **reply);

#endif // PACEMAKER_EXECD__H
