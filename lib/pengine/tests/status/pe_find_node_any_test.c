/*
 * Copyright 2022-2024 the Pacemaker project contributors
 *
 * The version control history for this file may have further details.
 *
 * This source code is licensed under the GNU General Public License version 2
 * or later (GPLv2+) WITHOUT ANY WARRANTY.
 */

#include <crm_internal.h>

#include <crm/common/unittest_internal.h>
#include <crm/pengine/internal.h>

static void
empty_list(void **state) {
    assert_null(pe_find_node_any(NULL, NULL, NULL));
    assert_null(pe_find_node_any(NULL, NULL, "cluster1"));
    assert_null(pe_find_node_any(NULL, "id1", NULL));
    assert_null(pe_find_node_any(NULL, "id1", "cluster1"));
}

static void
non_null_list(void **state) {
    GList *nodes = NULL;

    pcmk_node_t *a = pcmk__assert_alloc(1, sizeof(pcmk_node_t));
    pcmk_node_t *b = pcmk__assert_alloc(1, sizeof(pcmk_node_t));

    a->details = pcmk__assert_alloc(1, sizeof(struct pe_node_shared_s));
    a->private = pcmk__assert_alloc(1, sizeof(struct pcmk__node_private));

    b->details = pcmk__assert_alloc(1, sizeof(struct pe_node_shared_s));
    b->private = pcmk__assert_alloc(1, sizeof(struct pcmk__node_private));

    a->details->uname = "cluster1";
    a->private->id = "id1";

    b->details->uname = "cluster2";
    b->private->id = "id2";

    nodes = g_list_append(nodes, a);
    nodes = g_list_append(nodes, b);

    assert_ptr_equal(b, pe_find_node_any(nodes, "id2", NULL));
    assert_ptr_equal(b, pe_find_node_any(nodes, "ID2", NULL));

    assert_ptr_equal(a, pe_find_node_any(nodes, "xyz", "cluster1"));
    assert_ptr_equal(a, pe_find_node_any(nodes, NULL, "cluster1"));

    assert_null(pe_find_node_any(nodes, "id10", NULL));
    assert_null(pe_find_node_any(nodes, "nodeid1", NULL));
    assert_null(pe_find_node_any(nodes, NULL, "cluster10"));
    assert_null(pe_find_node_any(nodes, NULL, "nodecluster1"));
    assert_null(pe_find_node_any(nodes, "id3", "cluster3"));
    assert_null(pe_find_node_any(nodes, NULL, NULL));

    free(a->private);
    free(a->details);
    free(a);
    free(b->private);
    free(b->details);
    free(b);
    g_list_free(nodes);
}

PCMK__UNIT_TEST(NULL, NULL,
                cmocka_unit_test(empty_list),
                cmocka_unit_test(non_null_list))
