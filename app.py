import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
import uuid
from groq import Groq

st.set_page_config(
    page_title="OrgX HR Portal",
    page_icon="🏢",
    layout="wide"
)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
CC_OPTIONS = ["None", "My Reporting Manager", "HR Business Partner", "Finance Team", "Legal Team"]
CC_MAP = {
    "My Reporting Manager": "manager@orgx.com",
    "HR Business Partner": "hrbp@orgx.com",
    "Finance Team": "finance@orgx.com",
    "Legal Team": "legal@orgx.com",
}
BUS_UNITS = ["Select...", "Consumer Products", "Financial Services",
             "Technology Solutions", "Infrastructure", "Corporate Functions"]
DEPARTMENTS = ["Select...", "Finance", "HR", "Operations", "Support",
               "Marketing", "Engineering", "Sales"]

HR_POLICY_CONTEXT = """
You are the OrgX HR Assistant — an AI-powered self-service tool for OrgX employees.
You answer questions based ONLY on the following OrgX HR policies. If a question is outside
these policies, say so clearly.

POLICY 1: LEAVE POLICY
Confirmed employees get 24 days paid leave per year. Probation employees (first 6 months) get 2 days per month; remaining days credited upon confirmation.
Sick Leave: 12 days per year. Doctor note required for absences over 3 consecutive days.
Public Holidays: 8 fixed holidays per year across Delhi, Mumbai, Bangalore, Chennai, Hyderabad.
Sabbatical: After 5 years, up to 3 months unpaid. 6 months notice required. 3-year cooling-off period after.
Leave Carry Forward: Max 6 days. No leave encashment during employment.
Comp Off: Full day if worked 6+ hours on non-working day. Half day if 4-6 hours. Use within 1 month. Manager approval required.
Pro-Rated Leave first month: Joining 1st-15th = 1.5 days. Joining 16th-25th = 1 day. Joining 26th-31st = 0 days.
All leaves via HRMS portal.

POLICY 2: REIMBURSEMENT
Meal: INR 500 per meal, up to 3 meals per day when travelling. Bills required.
Conveyance: Not for daily commute. Reimbursed on actuals for official travel.
Work equipment: Up to INR 10,000 per year for confirmed employees. Receipt required within 30 days.
Manager team meals: INR 10,000 per quarter. Does not carry forward.
Claims via HRMS. Approved in 5 working days, paid next month salary.

POLICY 3: PERFORMANCE APPRAISAL
Appraisal in January. Ratings by end February. Increments from 1st April.
Eligibility: 12 months service by 1st October of appraisal year. Probation employees not eligible.
Process: Self Review > Manager Review > Leadership Calibration > Finance and P&C > Final Ratings.
KRAs set with manager within 30 days of joining.
Rating scale: 1 (Does Not Meet) to 5 (Exceptional).

POLICY 4: PAYROLL AND PAYSLIP
Salary on or before last working day each month.
Components: Basic (40-50% CTC), HRA (40-50% Basic), Special Allowance, PF (12% Basic, max INR 1800/month), Professional Tax, TDS.
Payslips on HRMS by 5th of next month. Password: date of birth DDMMYYYY.
Tax declaration at start of financial year (April). Investment proofs Jan-Feb. Old or New Tax Regime, cannot change mid-year.
Full and Final settlement within 45 days of last working day.
UAN on payslip and HRMS under My Documents.

POLICY 5: GRIEVANCE AND ESCALATION
Tier 1: Speak with manager. 5 working days.
Tier 2: Email pc@orgx.com or HR portal. Acknowledged 2 days, resolved 15 working days.
Tier 3: Email headpc@orgx.com within 5 days of Tier 2 outcome. Final in 10 working days.
POSH: posh-ic@orgx.com. Confidential under POSH Act 2013.
No retaliation. All grievances confidential.

IMPORTANT: If question is outside these policies, say exactly: "I'm sorry, I don't have information on that in my current knowledge base. I'd recommend raising a support ticket so our People & Culture team can assist you directly."
"""

# ── HELPERS ───────────────────────────────────────────────────────────────────
def gen_ref(prefix):
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

def build_recipients(primary, cc_dropdown, cc_custom):
    recipients = [primary]
    cc_list = []
    if cc_dropdown and cc_dropdown != "None" and cc_dropdown in CC_MAP:
        cc_list.append(CC_MAP[cc_dropdown])
    if cc_custom:
        for email in [e.strip() for e in cc_custom.split(",")]:
            if "@" in email and email not in cc_list:
                cc_list.append(email)
    return recipients, cc_list

def send_email(subject, html_body, gmail_user, gmail_password, recipients, cc_list=[]):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = ", ".join(recipients)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, recipients + cc_list, msg.as_string())
        return True
    except Exception as e:
        st.session_state["email_error"] = str(e)
        return False

def email_template(title, subtitle, ref_id, rows, footer_note, cc_list):
    rows_html = "".join([f"<p><b>{k}:</b> {v}</p>" for k, v in rows.items()])
    cc_section = f"<p><b>CC:</b> {', '.join(cc_list)}</p>" if cc_list else ""
    return f"""
    <html><body style="font-family:Arial,sans-serif;padding:20px;">
    <div style="max-width:620px;margin:0 auto;background:white;border-radius:12px;border:1px solid #e0e0e0;">
    <div style="background:#1F4E79;padding:20px 30px;">
    <h2 style="color:white;margin:0;">OrgX HR Service Portal</h2>
    <p style="color:#BDD7EE;margin:4px 0 0;">{title}</p>
    </div>
    <div style="padding:25px 30px;">
    <div style="background:#FFF3E0;border-left:4px solid #FF9800;padding:10px 16px;
    border-radius:0 8px 8px 0;margin-bottom:20px;">
    <p style="margin:0;font-size:0.8rem;color:#E65100;font-weight:bold;
    text-transform:uppercase;letter-spacing:0.5px;">Reference ID</p>
    <p style="margin:4px 0 0;font-size:1rem;font-weight:bold;">{ref_id}</p>
    </div>
    {rows_html}
    {cc_section}
    <hr/>
    <p style="color:#6b7280;font-size:0.85rem;">{footer_note}</p>
    </div>
    <div style="background:#f8f7f4;padding:12px 30px;text-align:center;">
    <p style="color:#9ca3af;font-size:0.75rem;margin:0;">
    OrgX HR Portal · Confidential · Do not forward</p>
    </div>
    </div></body></html>
    """

def cc_fields(key_prefix):
    c1, c2 = st.columns(2)
    with c1:
        dropdown = st.selectbox("Copy in (CC)", CC_OPTIONS, key=f"{key_prefix}_cc_drop")
    with c2:
        custom = st.text_input("Additional emails",
            placeholder="a@orgx.com, b@orgx.com", key=f"{key_prefix}_cc_custom")
    return dropdown, custom

def success_block(ref_id, label="Submission"):
    st.success(f"✅ {label} submitted successfully! Reference ID: **{ref_id}**")
    st.info("The People & Culture team will acknowledge within 24 hours.")

def get_groq_response(user_messages, api_key):
    client = Groq(api_key=api_key)
    messages = [{"role": "system", "content": HR_POLICY_CONTEXT}]
    for msg in user_messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=1024,
        temperature=0.3
    )
    return response.choices[0].message.content

# ── SESSION STATE ─────────────────────────────────────────────────────────────
defaults = {
    "messages": [], "last_query": "",
    "resignation_done": False, "resignation_ref": "",
    "docreq_done": False, "docreq_ref": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏢 OrgX HR Portal")
    st.divider()
    page = st.radio("", [
        "🤖 HR Assistant",
        "🚪 Resignation",
        "📄 Document Request",
    ], label_visibility="collapsed")
    st.divider()
    st.markdown("### ⚙️ Configuration")
    api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    gmail_user = st.text_input("Gmail (sender)", placeholder="yourname@gmail.com")
    gmail_password = st.text_input("Gmail App Password", type="password",
        placeholder="xxxx xxxx xxxx xxxx")
    recipient_email = st.text_input("P&C Team Email", placeholder="pc-team@orgx.com")
    st.divider()
    st.caption("Get your free Groq key at console.groq.com")
    if page == "🤖 HR Assistant":
        if st.button("Clear conversation"):
            st.session_state.messages = []
            st.session_state.last_query = ""
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HR ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
if page == "🤖 HR Assistant":
    st.title("OrgX HR Assistant")
    st.caption("Ask me about leave, reimbursements, appraisals, payroll, or grievances.")
    st.divider()

    if not st.session_state.messages:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown("""Hello! I am the OrgX HR Assistant. I can help you with:

- **Leave** — entitlements, carry-forward, sick leave, sabbatical
- **Reimbursements** — meals, travel, equipment
- **Appraisals** — process, eligibility, KRAs
- **Payroll** — payslips, salary structure, tax
- **Grievances** — how to raise a concern

For resignation or document requests use the sidebar. What can I help you with today?""")

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.write(msg["content"])
                if msg.get("escalation"):
                    st.warning("This is outside my knowledge base. "
                               "Use **Raise a Ticket** in the sidebar.")

    user_input = st.chat_input("Type your HR question here...")
    if user_input:
        if not api_key:
            st.error("Please enter your Groq API key in the sidebar.")
            st.stop()
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.write(user_input)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                try:
                    response_text = get_groq_response(st.session_state.messages, api_key)
                    st.write(response_text)
                    phrases = ["don't have information", "outside my current knowledge",
                               "raise a support ticket", "i'm sorry, i don't have"]
                    needs_escalation = any(p in response_text.lower() for p in phrases)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "escalation": needs_escalation
                    })
                    if needs_escalation:
                        st.session_state.last_query = user_input
                        st.warning("This is outside my knowledge base. "
                                   "Use the sidebar to reach the P&C team.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.messages.pop()
    st.caption("OrgX HR Assistant · Powered by Groq AI · For HR queries only")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: RESIGNATION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🚪 Resignation":
    st.title("Resignation Notice")
    st.caption("Formally submit your resignation. The P&C team will acknowledge within 24 hours.")
    st.divider()

    if st.session_state.resignation_done:
        success_block(st.session_state.resignation_ref, "Resignation Notice")
        st.info("Please ensure all handover documentation is completed "
                "before your last working day.")
        if st.button("Submit another"):
            st.session_state.resignation_done = False
            st.rerun()
    else:
        st.markdown("### Employee Details")
        c1, c2 = st.columns(2)
        with c1:
            r_name = st.text_input("Full Name *")
            r_id = st.text_input("Employee ID *")
            r_email = st.text_input("Work Email *")
            r_design = st.text_input("Designation *")
        with c2:
            r_bu = st.selectbox("Business Unit *", BUS_UNITS)
            r_dept = st.selectbox("Department *", DEPARTMENTS)
            r_doj = st.date_input("Date of Joining *",
                min_value=date(2000, 1, 1), max_value=date.today())

        st.divider()
        st.markdown("### Resignation Details")

        r_reason_choice = st.selectbox("Primary Reason for Resignation *", [
            "Select...",
            "Better career opportunity",
            "Higher compensation elsewhere",
            "Personal reasons",
            "Relocation",
            "Further education",
            "Health reasons",
            "Work-life balance",
            "Organisational culture",
            "Role not aligned with expectations",
            "Other"])

        r_reason_other = ""
        if r_reason_choice == "Other":
            r_reason_other = st.text_input("Please specify your reason *",
                placeholder="Enter your reason here...")

        r_reason = r_reason_other if r_reason_choice == "Other" else r_reason_choice

        st.divider()
        st.markdown("### Notice Period Buyout")
        r_buyout = st.checkbox("I would like to explore the notice period buyout option")
        if r_buyout:
            st.info(
                "ℹ️ Notice period buyout is subject to company policy and is granted at the "
                "sole discretion of OrgX based on handover completion and replacement "
                "requirements. Selecting this option does not guarantee approval. "
                "The People & Culture team will confirm eligibility upon reviewing your resignation."
            )

        r_comments = st.text_area("Additional Comments (optional)", height=80,
            placeholder="Any additional context or handover notes...")

        st.divider()
        st.markdown("**CC (optional)**")
        r_cc_custom = st.text_input(
            "Email address(es) to copy",
            placeholder="e.g. your.manager@orgx.com, colleague@orgx.com",
            help="Enter your reporting manager's email or any other recipient. "
                 "Separate multiple emails with a comma.")

        st.divider()
        st.warning("⚠️ Submitting this form formally initiates your resignation "
                   "and triggers the offboarding process.")

        if st.button("Submit Resignation →", type="primary"):
            errors = []
            if not r_name: errors.append("Full Name")
            if not r_id: errors.append("Employee ID")
            if not r_email: errors.append("Work Email")
            if not r_design: errors.append("Designation")
            if r_bu == "Select...": errors.append("Business Unit")
            if r_dept == "Select...": errors.append("Department")
            if r_reason_choice == "Select...": errors.append("Reason for Resignation")
            if r_reason_choice == "Other" and not r_reason_other:
                errors.append("Please specify your reason")
            if errors:
                st.error(f"Please fill in: {', '.join(errors)}")
            elif not all([gmail_user, gmail_password, recipient_email]):
                st.error("Please configure Gmail in the sidebar.")
            else:
                ref = gen_ref("RES")
                ts = datetime.now().strftime("%d %B %Y, %I:%M %p")
                buyout_label = "Yes — pending P&C review and approval" if r_buyout else "No"
                cc_list = []
                if r_cc_custom:
                    for e in [x.strip() for x in r_cc_custom.split(",")]:
                        if "@" in e:
                            cc_list.append(e)
                recipients = [recipient_email]
                body = email_template(
                    "Resignation Notice Submitted", r_reason, ref,
                    {"Name": r_name, "Employee ID": r_id, "Email": r_email,
                     "Business Unit": r_bu, "Department": r_dept,
                     "Designation": r_design,
                     "Date of Joining": str(r_doj),
                     "Reason for Resignation": r_reason,
                     "Notice Period Buyout Requested": buyout_label,
                     "Additional Comments": r_comments or "None",
                     "Submitted": ts},
                    "Please initiate the offboarding process and acknowledge within 24 hours. "
                    "If a buyout has been requested, please confirm eligibility with the employee.",
                    cc_list
                )
                ok = send_email(
                    f"[OrgX Resignation] {ref} — {r_name} | {r_bu}",
                    body, gmail_user, gmail_password, recipients, cc_list)
                if ok:
                    st.session_state.resignation_done = True
                    st.session_state.resignation_ref = ref
                    st.rerun()
                else:
                    err = st.session_state.get("email_error", "Unknown error")
                    st.error(f"Submission failed: {err}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DOCUMENT REQUEST
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📄 Document Request":
    st.title("Document Request")
    st.caption("Standard documents are issued within 3 working days.")
    st.divider()

    if st.session_state.docreq_done:
        success_block(st.session_state.docreq_ref, "Document Request")
        if st.button("Submit another"):
            st.session_state.docreq_done = False
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            d_name = st.text_input("Full Name *")
            d_id = st.text_input("Employee ID *")
            d_email = st.text_input("Work Email *")
            d_bu = st.selectbox("Business Unit *", BUS_UNITS)
        with c2:
            d_type = st.selectbox("Document Type *", [
                "Select...",
                "Employment Verification Letter",
                "Salary Certificate",
                "Experience Letter",
                "Relieving Letter",
                "Payslip (specific month)",
                "Form 16",
                "PF Statement",
                "Offer Letter Copy",
                "NOC Letter",
                "Other"])
            d_purpose = st.text_input("Purpose / Reason *",
                placeholder="e.g. Visa application, bank loan, background check")
            d_urgent = st.checkbox("Mark as Urgent (required within 24 hours)")

        d_comments = st.text_area("Additional Details (optional)", height=80,
            placeholder="Any specific instructions, date range, or formatting requirements...")
        st.markdown("**CC (optional)**")
        d_cc_drop, d_cc_custom = cc_fields("docreq")
        st.divider()

        if st.button("Submit Document Request →", type="primary"):
            errors = []
            if not d_name: errors.append("Full Name")
            if not d_id: errors.append("Employee ID")
            if not d_email: errors.append("Work Email")
            if not d_purpose: errors.append("Purpose")
            if d_bu == "Select...": errors.append("Business Unit")
            if d_type == "Select...": errors.append("Document Type")
            if errors:
                st.error(f"Please fill in: {', '.join(errors)}")
            elif not all([gmail_user, gmail_password, recipient_email]):
                st.error("Please configure Gmail in the sidebar.")
            else:
                ref = gen_ref("DOC")
                ts = datetime.now().strftime("%d %B %Y, %I:%M %p")
                urgent_label = "YES — Required within 24 hours" if d_urgent else "No"
                recipients, cc_list = build_recipients(
                    recipient_email, d_cc_drop, d_cc_custom)
                body = email_template(
                    "Document Request", d_type, ref,
                    {"Name": d_name, "Employee ID": d_id, "Email": d_email,
                     "Business Unit": d_bu, "Document Type": d_type,
                     "Purpose": d_purpose, "Urgent": urgent_label,
                     "Additional Details": d_comments or "None",
                     "Submitted": ts},
                    "Standard documents issued within 3 working days. "
                    "Urgent requests within 24 hours.", cc_list
                )
                ok = send_email(
                    f"[OrgX Document] {ref} — {d_type} | {d_name}",
                    body, gmail_user, gmail_password, recipients, cc_list)
                if ok:
                    st.session_state.docreq_done = True
                    st.session_state.docreq_ref = ref
                    st.rerun()
                else:
                    err = st.session_state.get("email_error", "Unknown error")
                    st.error(f"Submission failed: {err}")

st.divider()
st.caption("OrgX HR Portal · All submissions are confidential and "
           "processed by the People & Culture team")
