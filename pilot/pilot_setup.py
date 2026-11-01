import frappe

frappe.init(site="eorl-demo.localhost", sites_path="/workspace/development/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

MODEL = "Qwen3 27B (vLLM, T0.6)"
BASE_MODEL = "Qwen3 27B (vLLM)"


def get_or_create(doctype, name_field, name, fields):
    if frappe.db.exists(doctype, name):
        print("exists:", doctype, name)
        return frappe.get_doc(doctype, name)
    doc = frappe.get_doc({"doctype": doctype, name_field: name, **fields}).insert(ignore_permissions=True)
    print("created:", doctype, doc.name)
    return doc


base = frappe.get_doc("EORL Model Profile", BASE_MODEL)
get_or_create(
    "EORL Model Profile", "profile_name", MODEL,
    dict(
        provider="openai_compatible", enabled=1, base_url=base.base_url, model_name=base.model_name,
        api_key_reference=base.api_key_reference, temperature=0.6, top_p=0.95, max_tokens=4096,
        timeout_seconds=180, max_retries=3,
    ),
)

# --- tool policies: same flags as the scripted policies; finish_turn added; messaging excluded in every arm
def policy(name, flags, tools):
    return get_or_create(
        "EORL Tool Policy", "policy_name", name,
        dict(**flags, allowed_semantic_tools=[{"tool_name": t} for t in tools + ["finish_turn"]]),
    )

policy("Pilot Purchasing Agent Policy", dict(has_execution_authority=1, may_submit_documents=0),
       ["get_supplier_options", "create_purchase_order"])
policy("Pilot Purchasing Manager Policy", dict(has_execution_authority=1, may_approve=1, may_submit_documents=1),
       ["get_purchase_order", "submit_purchase_order"])
policy("Pilot Warehouse Agent Policy", dict(has_execution_authority=1, may_submit_documents=1),
       ["get_purchase_order", "create_purchase_receipt", "submit_purchase_receipt", "inspect_received_goods",
        "escalate_quality_exception"])
policy("Pilot Accounts Payable Policy", dict(has_execution_authority=1, may_submit_documents=1),
       ["get_receipt_status", "create_purchase_invoice", "submit_purchase_invoice", "create_payment_entry",
        "submit_payment_entry"])
policy("Pilot General Purchasing Policy", dict(has_execution_authority=1, may_approve=1, may_submit_documents=1),
       ["get_supplier_options", "get_purchase_order", "get_receipt_status", "create_purchase_order",
        "submit_purchase_order", "create_purchase_receipt", "submit_purchase_receipt", "create_purchase_invoice",
        "submit_purchase_invoice", "create_payment_entry", "submit_payment_entry", "inspect_received_goods",
        "escalate_quality_exception"])

COMMON = (
    "You are one role in a procure-to-pay routine that runs against a real ERPNext system. You have no "
    "information about suppliers, prices, or quality except what tool results tell you."
)
INSTR = {
    "Pilot Purchasing Agent": ("Purchasing Agent", "Pilot Purchasing Agent Policy", None,
        COMMON + " You are the purchasing agent, the first of four roles; a purchasing manager, a warehouse agent, "
        "and an accounts payable agent handle the later steps. Your part: sense supplier options and create a "
        "purchase order, then call finish_turn."),
    "Pilot Purchasing Manager Agent": ("Purchasing Manager Agent", "Pilot Purchasing Manager Policy", None,
        COMMON + " You are the purchasing manager agent, the second of four roles. Your part: review the purchase "
        "order handed to you and submit it, then call finish_turn."),
    "Pilot Warehouse Agent": ("Warehouse Agent", "Pilot Warehouse Agent Policy", None,
        COMMON + " You are the warehouse agent, the third of four roles. Your part: create and submit a purchase "
        "receipt for the approved purchase order handed to you, inspect the received goods, then call finish_turn. If the inspection finds a quality problem, decide how to handle it with the tools you have."),
    "Pilot Accounts Payable Agent": ("Accounts Payable Agent", "Pilot Accounts Payable Policy", None,
        COMMON + " You are the accounts payable agent, the last of four roles. Your part: create and submit a "
        "purchase invoice for the receipt handed to you, then create and submit a payment entry, then call "
        "finish_turn."),
    "Pilot General Purchasing Agent": ("General Purchasing Agent", "Pilot General Purchasing Policy", None,
        COMMON + " You perform every step of the routine yourself: sense supplier options, create and submit a "
        "purchase order, create and submit a purchase receipt, inspect received goods, create and submit a "
        "purchase invoice, create and submit a payment entry, then call finish_turn. If the inspection finds a quality problem, decide how to handle it with the tools you have."),
}
for name, (role, pol, mem, text) in INSTR.items():
    get_or_create(
        "EORL Agent Template", "template_name", name,
        dict(organizational_role=role, enabled=1, model_profile=MODEL, tool_policy=pol,
             memory_profile=mem, initial_system_instructions=text),
    )

get_or_create(
    "EORL Architecture", "architecture_name", "Pilot Specialist Handoff (Qwen3)",
    dict(coordination_mode="specialist_handoff", description="Four live-model specialists, explicit handoffs, no messaging.",
         actor_slots=[
             {"slot_id": "purchasing_agent", "agent_template": "Pilot Purchasing Agent"},
             {"slot_id": "purchasing_manager_agent", "agent_template": "Pilot Purchasing Manager Agent"},
             {"slot_id": "warehouse_agent", "agent_template": "Pilot Warehouse Agent"},
             {"slot_id": "accounts_payable_agent", "agent_template": "Pilot Accounts Payable Agent"},
         ]),
)
get_or_create(
    "EORL Architecture", "architecture_name", "Pilot Broad Autonomy (Qwen3)",
    dict(coordination_mode="broad_autonomy", description="One live-model actor performs every stage, no memory.",
         actor_slots=[{"slot_id": "general_purchasing_agent", "agent_template": "Pilot General Purchasing Agent"}]),
)
frappe.db.commit()
print("setup done")
frappe.destroy()
