import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
import uuid
from groq import Groq
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="OrgX HR Portal",
    page_icon="🏢",
    layout="wide"
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    .block-container { padding-left: 2rem; padding-right: 2rem; }
</style>
""", unsafe_allow_html=True)

# ── LOAD SECRETS ──────────────────────────────────────────────────────────────
try:
    GROQ_API_KEY    = st.secrets["GROQ_API_KEY"]
    GMAIL_USER      = st.secrets["GMAIL_USER"]
    GMAIL_PASSWORD  = st.secrets["GMAIL_PASSWORD"]
    RECIPIENT_EMAIL = st.secrets["RECIPIENT_EMAIL"]
    SHEET_URL       = st.secrets.get("SHEET_URL", "")
    GCP_CREDS       = dict(st.secrets.get("gcp_service_account", {}))
    SECRETS_OK      = True
except Exception:
    SECRETS_OK = False

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
BUS_UNITS = [
    "Select...", "Consumer Products", "Financial Services",
    "Technology Solutions", "Infrastructure", "Corporate Functions"
]
DEPARTMENTS = [
    "Select...", "Finance", "HR", "Operations",
    "Support", "Marketing", "Engineering", "Sales"
]

HR_POLICY_CONTEXT = """
You are the OrgX HR Assistant — an AI-powered self-service tool for OrgX employees.
You answer questions based ONLY on the following OrgX HR policies. If a question is outside
these policies, say so clearly.

POLICY 1: LEAVE POLICY

Paid Leave (Discretionary Leave):
- Confirmed employees: 24 days per year, credited in full upon confirmation.
- Probationary employees (first 6 months): 2 days per month accrued monthly. Upon confirmation the remaining annual balance is credited immediately.
- Maximum 6 days may be carried forward to the next calendar year. Any unused days beyond 6 are forfeited at year end.
- No leave is encashable during the course of employment. Leave encashment calculations apply only upon separation from OrgX.

Sick Leave:
- All employees (confirmed and probationary): 12 days per year, credited at the start of each calendar year.
- For absences exceeding 3 consecutive business days, a doctor's note must be submitted to the P&C team and the reporting manager via email.
- Sick leave cannot be carried forward or encashed.

Public Holidays:
- All employees across Delhi, Mumbai, Bangalore, Chennai, and Hyderabad receive 8 fixed public holidays per year.
- The list is published by the P&C team at the start of each year and is uniform across all locations.

Sabbatical:
- Available after 5 years of continuous service.
- Duration: up to 3 months, unpaid.
- Requires 6 months prior written notice approved by the business unit head.
- A 3-year cooling-off period applies before a subsequent sabbatical can be requested.

Compensatory Off (Comp Off):
- Full day comp off: worked 6 or more hours on a non-working day.
- Half day comp off: worked between 4 and 6 hours on a non-working day.
- Prior written manager approval required before working on a non-working day.
- Comp offs must be used within 1 month of being credited. Unused comp offs lapse.

Pro-Rated Leave — First Month of Joining:
- Joining 1st to 15th: 1.5 days credited.
- Joining 16th to 25th: 1 day credited.
- Joining 26th to 31st: 0 days credited.

Intern Leave:
- Interns receive 2 discretionary leave days per month of their internship.
- Unused intern leave carries forward within the internship period.
- Interns are entitled to public holidays that fall within their tenure.
- No leave type is encashable for interns.

All leave must be applied for via the OrgX HRMS portal.

POLICY 2: REIMBURSEMENT POLICY

Meal Reimbursement:
- INR 500 per meal, up to 3 meals per day when travelling for official work.
- Original bills or digital receipts are mandatory for all meal claims.
- Personal meals at the regular place of work during standard hours are not reimbursable.

Manager Team Meals:
- Managers with direct reports are allocated INR 10,000 per quarter for team meals.
- Must be submitted with original bills and a note of the occasion.
- Unused budget does not carry forward to the next quarter.

Conveyance:
- Daily commute between home and regular place of work is not reimbursable.
- Local conveyance during official travel (client visits, inter-office travel, field work) is reimbursed on actuals.
- Receipts or app-generated invoices required.

Work Equipment:
- All confirmed employees may claim up to INR 10,000 per calendar year for work-related equipment.
- Eligible items include: mouse, keyboard, headphones, webcam, desk lamp, and other productivity accessories.
- Personal electronics or items for general home use are not eligible.
- Original receipt required. Claims must be submitted within 30 days of purchase.
- This entitlement does not carry forward to the next year.

Claim Process:
- All claims submitted via the OrgX HRMS portal under Expense Claims.
- Approved by reporting manager within 5 working days.
- Reimbursed via payroll in the following month's salary cycle.
- Rejected claims are communicated with reasons within 5 working days.

POLICY 3: PERFORMANCE APPRAISAL

Cycle: Annual appraisal in January each year. Ratings and increment letters issued by end of February. Increments effective from 1st April.

Eligibility: Employees must have completed 12 months of continuous service by 1st October of the appraisal year. Probationary employees are not eligible. Employees who joined after 1st October will be eligible from the following year's cycle.

Process:
Step 1 — Self Review: Employee completes self-assessment against KRAs in the HRMS.
Step 2 — Manager Review: Reporting manager reviews and assigns a preliminary rating.
Step 3 — Leadership Calibration: Business unit leaders review ratings for consistency across teams.
Step 4 — Finance and P&C Processing: Increments are calculated and processed.
Step 5 — Final Ratings and Increments Announced: Communicated to employees by end of February.

KRAs: Must be set with the reporting manager within 30 days of joining or the start of the performance year. KRAs should be specific, measurable, and aligned to team and business unit objectives.

Rating Scale:
- 5: Exceptional — significantly exceeded all KRAs with outstanding impact.
- 4: Exceeds Expectations — exceeded most KRAs with strong performance.
- 3: Meets Expectations — met all KRAs consistently.
- 2: Partially Meets — met some KRAs but fell short in key areas.
- 1: Does Not Meet — did not meet KRA expectations for the cycle.

POLICY 4: PAYROLL AND PAYSLIP

Salary Payment: Credited on or before the last working day of each month. In the event of a banking holiday, disbursement may be preponed by 1-2 working days.

Salary Components:
- Basic Salary: 40-50% of CTC.
- House Rent Allowance (HRA): 40-50% of Basic.
- Special Allowance: Balancing component.
- Provident Fund (PF) — Employee Contribution: 12% of Basic Salary is the statutory minimum contribution under the Employees' Provident Funds and Miscellaneous Provisions Act, 1952. The statutory wage ceiling for PF is INR 15,000 per month, meaning the minimum employer and employee contribution is INR 1,800 per month each. However, if your Basic Salary exceeds INR 15,000, your actual PF deduction will be 12% of your actual Basic.
- Voluntary PF (VPF): Under Indian law, employees may voluntarily contribute more than the statutory 12% — up to 100% of their Basic Salary — through a Voluntary Provident Fund (VPF) election. VPF contributions attract the same interest rate as EPF (currently 8.25% per annum as notified by the government) and are eligible for tax deduction under Section 80C. If you would like to increase your PF contribution via VPF, please raise a ticket via the OrgX HR Service Portal or email finance@orgx.com — the Finance team will process your election for the next payroll cycle.
- Professional Tax: As per state government rules — varies by location.
- Income Tax (TDS): Based on declared tax regime and investment declarations.

Payslip Access: Available on the OrgX HRMS portal under Payslip by the 5th of the following month. Password is your date of birth in DDMMYYYY format. For access issues, raise a ticket via the HR Service Portal or email pc@orgx.com.

Tax Declaration:
- Submit planned tax-saving investments at the start of the financial year (April) via HRMS.
- Investment proof submission window: January to February each year.
- Employees who do not submit proofs will have TDS calculated on gross salary.
- OrgX supports both Old Tax Regime and New Tax Regime.
- Regime selection cannot be changed mid-year.

Salary Revision: Revised salary from the annual appraisal is effective from 1st April and reflected in the April payslip.

Full and Final Settlement (FnF): Processed within 45 days of the last working day. Includes salary for days worked, encashable leave if applicable, gratuity if eligible (after 5 years of service), and approved pending reimbursements.

UAN / PF Account Number: Available on your payslip and under My Documents on the HRMS portal.

POLICY 5: GRIEVANCE AND ESCALATION

OrgX is committed to a respectful, fair, and inclusive workplace. All grievances are handled confidentially. No retaliation is tolerated against any employee who raises a concern in good faith.

EMERGENCY OR URGENT CONCERNS:
If you are facing an immediate threat to your physical safety, witnessing ongoing harassment, or experiencing a situation that cannot wait for the standard grievance process, please do not wait. Contact the Head of People & Culture directly at headpc@orgx.com or call the P&C emergency line during business hours. For situations involving criminal activity or immediate physical danger, contact local law enforcement immediately. OrgX's Internal Committee for POSH matters also operates on an expedited basis — email posh-ic@orgx.com for immediate response.

Standard Grievance Process:

Tier 1 — Informal Resolution:
- Attempt to resolve informally by speaking with your reporting manager first.
- If the grievance involves your manager, approach the next level manager or the P&C team directly.
- Target resolution: within 5 working days.
- This step is encouraged but not mandatory — if the nature of the concern makes informal resolution inappropriate or unsafe, proceed directly to Tier 2.

Tier 2 — Formal Grievance:
- Submit a written complaint to the P&C team at pc@orgx.com or via the OrgX HR Service Portal.
- The P&C team will acknowledge within 2 working days and assign an HR Business Partner to investigate.
- Target resolution: within 15 working days of acknowledgement.
- For serious concerns such as harassment, discrimination, or safety issues, the P&C team may expedite the investigation timeline at their discretion.

Tier 3 — Senior Escalation:
- If unsatisfied with the Tier 2 outcome, escalate to the Head of People & Culture at headpc@orgx.com within 5 working days of receiving the Tier 2 resolution.
- Final resolution provided within 10 working days.
- The Tier 3 decision is final within OrgX's internal grievance process.
- If an employee remains unsatisfied after Tier 3, they retain the right to approach external bodies including the relevant Labour Commissioner or appropriate legal authorities under Indian employment law.

POSH — Sexual Harassment:
- Complaints related to sexual harassment are governed under the Prevention of Sexual Harassment (POSH) Act, 2013.
- Contact the Internal Committee directly at posh-ic@orgx.com. All complaints are handled with strict confidentiality.
- The IC is legally required to complete its inquiry within 90 days of receiving a written complaint under the POSH Act.
- Interim relief measures (such as transfer of the respondent or complainant) may be requested at the time of filing the complaint.
- Employees may also approach the Local Complaints Committee (LCC) if they feel the internal process is compromised.

External Support Options:
- National Commission for Women (NCW): ncwapps.nic.in for online complaints.
- Labour Commissioner: for disputes related to unfair treatment, wrongful termination, or wage issues.
- iCall (Tata Institute of Social Sciences): 9152987821 — free mental health support for workplace distress.

IMPORTANT INSTRUCTIONS:
1. Answer ONLY based on the policies above. Do not guess or make up information.
2. Be warm, clear, and concise. Use plain language.
3. If a question is partially covered, answer what you can and flag what is not covered.
4. If the question is completely outside the above policies, say: "I'm sorry, I don't have information on that in my current knowledge base. I'd recommend raising a support ticket so our People & Culture team can assist you directly."
5. For grievance queries, always remind the employee that a formal grievance can be raised via the OrgX HR Service Portal.
"""

SHEET_HEADERS = {
    "Resignations":      ["Ref ID","Timestamp","Name","Employee ID","Email",
                          "Business Unit","Department","Designation",
                          "Date of Joining","Reason","Buyout Requested",
                          "Comments","CC","Status"],
    "Document Requests": ["Ref ID","Timestamp","Name","Employee ID","Email",
                          "Business Unit","Document Type","Purpose",
                          "Urgent","Additional Details","CC","Status"],
    "Grievances":        ["Ref ID","Timestamp","Name","Employee ID","Email",
                          "Business Unit","Department","Grievance Type",
                          "Concerns","Tier 1 Attempted","Description",
                          "Desired Outcome","CC","Status"],
    "HR Assistant":      ["Ticket ID","Timestamp","Name","Employee ID",
                          "Query","Response","Escalated","Status"],
}

# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
def get_gsheet_client():
    if not GCP_CREDS or not SHEET_URL:
        return None
    try:
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(GCP_CREDS, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        return None

def log_to_sheet(tab_name, row_data):
    try:
        gc = get_gsheet_client()
        if not gc or not SHEET_URL:
            return
        sh = gc.open_by_url(SHEET_URL)
        try:
            ws = sh.worksheet(tab_name)
        except:
            ws = sh.add_worksheet(title=tab_name, rows=1000, cols=25)
            ws.append_row(SHEET_HEADERS[tab_name])
        existing = ws.get_all_values()
        if not existing:
            ws.append_row(SHEET_HEADERS[tab_name])
        ws.append_row(row_data)
    except Exception:
        pass  # Sheets logging is non-blocking — don't interrupt the user flow

# ── EMAIL ─────────────────────────────────────────────────────────────────────
def send_email(subject, html_body, cc_list=[]):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_USER
        msg["To"]      = RECIPIENT_EMAIL
        if cc_list:
            msg["Cc"]  = ", ".join(cc_list)
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, [RECIPIENT_EMAIL] + cc_list, msg.as_string())
        return True
    except Exception as e:
        st.session_state["email_error"] = str(e)
        return False

def email_template(title, ref_id, rows, footer_note, cc_list):
    rows_html  = "".join([f"<p><b>{k}:</b> {v}</p>" for k, v in rows.items()])
    cc_section = f"<p><b>CC:</b> {', '.join(cc_list)}</p>" if cc_list else ""
    return f"""
    <html><body style="font-family:Arial,sans-serif;padding:20px;">
    <div style="max-width:620px;margin:0 auto;background:white;
    border-radius:12px;border:1px solid #e0e0e0;">
    <div style="background:#1F4E79;padding:20px 30px;">
    <h2 style="color:white;margin:0;">OrgX HR Service Portal</h2>
    <p style="color:#BDD7EE;margin:4px 0 0;">{title}</p>
    </div>
    <div style="padding:25px 30px;">
    <div style="background:#FFF3E0;border-left:4px solid #FF9800;
    padding:10px 16px;border-radius:0 8px 8px 0;margin-bottom:20px;">
    <p style="margin:0;font-size:0.8rem;color:#E65100;font-weight:bold;
    text-transform:uppercase;letter-spacing:0.5px;">Reference ID</p>
    <p style="margin:4px 0 0;font-size:1rem;font-weight:bold;">{ref_id}</p>
    </div>
    {rows_html}{cc_section}
    <hr/>
    <p style="color:#6b7280;font-size:0.85rem;">{footer_note}</p>
    </div>
    <div style="background:#f8f7f4;padding:12px 30px;text-align:center;">
    <p style="color:#9ca3af;font-size:0.75rem;margin:0;">
    OrgX HR Portal · Confidential · Do not forward</p>
    </div></div></body></html>
    """

# ── HELPERS ───────────────────────────────────────────────────────────────────
def gen_ref(prefix):
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

def parse_cc(raw):
    if not raw:
        return []
    return [e.strip() for e in raw.split(",") if "@" in e.strip()]

def success_block(ref_id, label="Submission"):
    st.success(f"✅ {label} submitted successfully! Reference ID: **{ref_id}**")
    st.info("The People & Culture team will acknowledge within 24 hours.")

def get_groq_response(messages):
    client = Groq(api_key=GROQ_API_KEY)
    msgs = [{"role": "system", "content": HR_POLICY_CONTEXT}]
    for m in messages:
        msgs.append({"role": m["role"], "content": m["content"]})
    r = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=msgs,
        max_tokens=1024,
        temperature=0.3
    )
    return r.choices[0].message.content

# ── SESSION STATE ─────────────────────────────────────────────────────────────
defaults = {
    "messages": [], "last_query": "",
    "chat_name": "", "chat_emp_id": "", "chat_identity_set": False,
    "resignation_done": False, "resignation_ref": "",
    "docreq_done":      False, "docreq_ref":      "",
    "grievance_done":   False, "grievance_ref":    "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── SECRETS CHECK ─────────────────────────────────────────────────────────────
if not SECRETS_OK:
    st.error("⚠️ App secrets are not configured. Please add your secrets in "
             "Streamlit Cloud → Settings → Secrets before using this portal.")
    st.stop()

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#1F4E79;padding:1.5rem 2rem;
border-radius:12px;margin-bottom:1.5rem;">
<h1 style="color:white;margin:0;font-size:1.8rem;">🏢 OrgX HR Portal</h1>
<p style="color:#BDD7EE;margin:4px 0 0;font-size:0.9rem;">
People & Culture · Self-Service · Available 24/7</p>
</div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🤖  HR Assistant",
    "🚪  Resignation",
    "📄  Document Request",
    "⚠️  Grievance",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HR ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_title, col_clear = st.columns([6, 1])
    with col_title:
        st.markdown("### OrgX HR Assistant")
        st.caption("Ask me about leave, reimbursements, appraisals, payroll, or grievances.")
    with col_clear:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear", key="clear_chat", help="Clear conversation history"):
            st.session_state.messages = []
            st.session_state.chat_identity_set = False
            st.session_state.chat_name = ""
            st.session_state.chat_emp_id = ""
            st.rerun()
    st.divider()

    # ── IDENTITY GATE ─────────────────────────────────────────────────────────
    if not st.session_state.chat_identity_set:
        st.info("Please identify yourself before starting the conversation. "
                "This helps us log and follow up on your queries.")
        id_c1, id_c2 = st.columns(2)
        with id_c1:
            input_name = st.text_input("Your Full Name *", key="input_name")
        with id_c2:
            input_emp_id = st.text_input("Employee ID *", key="input_emp_id")
        if st.button("Start Chat →", type="primary", key="start_chat"):
            if not input_name or not input_emp_id:
                st.error("Please enter your name and employee ID to continue.")
            else:
                st.session_state.chat_name = input_name
                st.session_state.chat_emp_id = input_emp_id
                st.session_state.chat_identity_set = True
                st.rerun()
        st.stop()

    # ── IDENTITY CONFIRMED ────────────────────────────────────────────────────
    st.caption(f"Logged in as: **{st.session_state.chat_name}** "
               f"· Employee ID: **{st.session_state.chat_emp_id}**")
    st.divider()

    if not st.session_state.messages:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(f"""Hello {st.session_state.chat_name.split()[0]}! I am the OrgX HR Assistant. I can help you with:

- **Leave** — entitlements, carry-forward, sick leave, sabbatical
- **Reimbursements** — meals, travel, equipment
- **Appraisals** — process, eligibility, KRAs
- **Payroll** — payslips, salary structure, tax
- **Grievances** — how to raise a concern

For resignation, document requests, or grievances use the tabs above.""")

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.write(msg["content"])
                if msg.get("grievance"):
                    st.info("⚠️ To formally raise a grievance, use the "
                            "**⚠️ Grievance** tab at the top of this page. "
                            "All submissions are confidential and protected "
                            "by OrgX's no-retaliation policy.")
                elif msg.get("escalation"):
                    st.warning(
                        "This query is outside what I can answer from OrgX's "
                        "current policy documents. Here's what you can do:\n\n"
                        "📝 **Raise a Ticket** — use the Raise a Ticket tab to "
                        "send your query directly to the P&C team\n\n"
                        "🚪 **Resignation** — use the Resignation tab if you are "
                        "looking to submit your resignation\n\n"
                        "📄 **Document Request** — use the Document Request tab "
                        "if you need an official HR document\n\n"
                        "⚠️ **Grievance** — use the Grievance tab if you need to "
                        "raise a formal concern"
                    )

    user_input = st.chat_input("Type your question here...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.write(user_input)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                try:
                    response_text = get_groq_response(st.session_state.messages)
                    st.write(response_text)

                    grievance_triggers = [
                        "grievance", "complaint", "raise a concern",
                        "formal complaint", "harassment", "bullying",
                        "unfair treatment", "discrimination", "report",
                        "posh", "raise an issue", "formal grievance"
                    ]
                    is_grievance = any(
                        t in user_input.lower() for t in grievance_triggers
                    )
                    escalation_phrases = [
                        "don't have information", "outside my current knowledge",
                        "raise a support ticket", "i'm sorry, i don't have"
                    ]
                    needs_escalation = any(
                        p in response_text.lower() for p in escalation_phrases
                    )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "escalation": needs_escalation and not is_grievance,
                        "grievance": is_grievance
                    })

                    if is_grievance:
                        st.info("⚠️ To formally raise a grievance, use the "
                                "**⚠️ Grievance** tab at the top of this page. "
                                "All submissions are confidential and protected "
                                "by OrgX's no-retaliation policy.")
                    elif needs_escalation:
                        st.warning(
                            "This query is outside what I can answer from OrgX's "
                            "current policy documents. Here's what you can do:\n\n"
                            "📝 **Raise a Ticket** — use the Raise a Ticket tab to "
                            "send your query directly to the P&C team\n\n"
                            "🚪 **Resignation** — use the Resignation tab if you are "
                            "looking to submit your resignation\n\n"
                            "📄 **Document Request** — use the Document Request tab "
                            "if you need an official HR document\n\n"
                            "⚠️ **Grievance** — use the Grievance tab if you need to "
                            "raise a formal concern"
                        )

                    log_to_sheet("HR Assistant", [
                        gen_ref("BOT"),
                        datetime.now().strftime("%d %b %Y %H:%M"),
                        st.session_state.chat_name,
                        st.session_state.chat_emp_id,
                        user_input, response_text,
                        "Grievance" if is_grievance else (
                            "Yes" if needs_escalation else "No"),
                        "Closed"
                    ])
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.messages.pop()
    st.caption("Powered by Groq AI · Responses based on OrgX policy documents only")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RESIGNATION
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Resignation Notice")
    st.caption("Formally submit your resignation. The P&C team will acknowledge within 24 hours.")
    st.divider()

    if st.session_state.resignation_done:
        success_block(st.session_state.resignation_ref, "Resignation Notice")
        st.info("Please ensure all handover documentation is completed "
                "before your last working day.")
        if st.button("Submit another resignation"):
            st.session_state.resignation_done = False
            st.rerun()
    else:
        st.markdown("#### Employee Details")
        c1, c2 = st.columns(2)
        with c1:
            r_name   = st.text_input("Full Name *",    key="r_name")
            r_id     = st.text_input("Employee ID *",  key="r_id")
            r_email  = st.text_input("Work Email *",   key="r_email")
            r_design = st.text_input("Designation *",  key="r_design")
        with c2:
            r_bu   = st.selectbox("Business Unit *", BUS_UNITS,    key="r_bu")
            r_dept = st.selectbox("Department *",    DEPARTMENTS,  key="r_dept")
            r_doj  = st.date_input("Date of Joining *", key="r_doj",
                        min_value=date(2000,1,1), max_value=date.today())

        st.divider()
        st.markdown("#### Resignation Details")
        r_reason_choice = st.selectbox("Primary Reason *", [
            "Select...", "Better career opportunity",
            "Higher compensation elsewhere", "Personal reasons",
            "Relocation", "Further education", "Health reasons",
            "Work-life balance", "Organisational culture",
            "Role not aligned with expectations", "Other"
        ], key="r_reason_choice")

        r_reason_other = ""
        if r_reason_choice == "Other":
            r_reason_other = st.text_input("Please specify *",
                placeholder="Enter your reason...", key="r_reason_other")
        r_reason = r_reason_other if r_reason_choice == "Other" else r_reason_choice

        st.divider()
        st.markdown("#### Notice Period Buyout")
        r_buyout = st.checkbox(
            "I would like to explore the notice period buyout option",
            key="r_buyout"
        )
        if r_buyout:
            st.info("ℹ️ Notice period buyout is subject to company policy and granted "
                    "at the sole discretion of OrgX based on handover completion and "
                    "replacement requirements. Selecting this does not guarantee approval. "
                    "The P&C team will confirm eligibility upon reviewing your resignation.")

        r_comments = st.text_area("Additional Comments (optional)", height=80,
            key="r_comments",
            placeholder="Any additional context or handover notes...")

        st.divider()
        st.markdown("**CC (optional)**")
        r_cc = st.text_input("Email address(es) to copy",
            placeholder="e.g. your.manager@orgx.com, colleague@orgx.com",
            key="r_cc",
            help="Separate multiple emails with a comma.")

        st.divider()
        st.warning("⚠️ Submitting this form formally initiates your resignation "
                   "and triggers the offboarding process.")

        if st.button("Submit Resignation →", type="primary", key="resign_submit"):
            errors = []
            if not r_name:   errors.append("Full Name")
            if not r_id:     errors.append("Employee ID")
            if not r_email:  errors.append("Work Email")
            if not r_design: errors.append("Designation")
            if r_bu   == "Select...": errors.append("Business Unit")
            if r_dept == "Select...": errors.append("Department")
            if r_reason_choice == "Select...": errors.append("Reason")
            if r_reason_choice == "Other" and not r_reason_other:
                errors.append("Please specify your reason")
            if errors:
                st.error(f"Please fill in: {', '.join(errors)}")
            else:
                ref = gen_ref("RES")
                ts  = datetime.now().strftime("%d %B %Y, %I:%M %p")
                buyout_label = "Yes — pending P&C review" if r_buyout else "No"
                cc_list = parse_cc(r_cc)
                body = email_template(
                    "Resignation Notice Submitted", ref,
                    {"Name": r_name, "Employee ID": r_id, "Email": r_email,
                     "Business Unit": r_bu, "Department": r_dept,
                     "Designation": r_design, "Date of Joining": str(r_doj),
                     "Reason": r_reason,
                     "Notice Period Buyout Requested": buyout_label,
                     "Comments": r_comments or "None", "Submitted": ts},
                    "Please initiate the offboarding process and acknowledge within 24 hours. "
                    "If buyout requested, confirm eligibility with the employee.", cc_list
                )
                if send_email(f"[OrgX Resignation] {ref} — {r_name} | {r_bu}",
                              body, cc_list):
                    log_to_sheet("Resignations", [
                        ref, ts, r_name, r_id, r_email, r_bu, r_dept,
                        r_design, str(r_doj), r_reason, buyout_label,
                        r_comments, ", ".join(cc_list), "Received"
                    ])
                    st.session_state.resignation_done = True
                    st.session_state.resignation_ref  = ref
                    st.rerun()
                else:
                    st.error(f"Submission failed: "
                             f"{st.session_state.get('email_error','Unknown error')}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — DOCUMENT REQUEST
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Document Request")
    st.caption("Standard documents issued within 3 working days. Urgent within 24 hours.")
    st.divider()

    if st.session_state.docreq_done:
        success_block(st.session_state.docreq_ref, "Document Request")
        if st.button("Submit another request"):
            st.session_state.docreq_done = False
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            d_name  = st.text_input("Full Name *",   key="d_name")
            d_id    = st.text_input("Employee ID *", key="d_id")
            d_email = st.text_input("Work Email *",  key="d_email")
            d_bu    = st.selectbox("Business Unit *", BUS_UNITS, key="d_bu")
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
                "Other"
            ], key="d_type")
            d_purpose = st.text_input("Purpose / Reason *",
                placeholder="e.g. Visa application, bank loan",
                key="d_purpose")
            d_urgent = st.checkbox("Mark as Urgent (within 24 hours)", key="d_urgent")

        d_type_other = ""
        if d_type == "Other":
            d_type_other = st.text_input("Please specify document required *",
                key="d_type_other")

        d_comments = st.text_area("Additional Details (optional)", height=80,
            key="d_comments",
            placeholder="Specific instructions, date range, formatting requirements...")

        st.divider()
        st.markdown("**CC (optional)**")
        d_cc = st.text_input("Email address(es) to copy",
            placeholder="e.g. your.manager@orgx.com",
            key="d_cc",
            help="Separate multiple emails with a comma.")

        st.divider()
        if st.button("Submit Document Request →", type="primary", key="docreq_submit"):
            errors = []
            if not d_name:    errors.append("Full Name")
            if not d_id:      errors.append("Employee ID")
            if not d_email:   errors.append("Work Email")
            if not d_purpose: errors.append("Purpose")
            if d_bu   == "Select...": errors.append("Business Unit")
            if d_type == "Select...": errors.append("Document Type")
            if d_type == "Other" and not d_type_other:
                errors.append("Please specify the document required")
            if errors:
                st.error(f"Please fill in: {', '.join(errors)}")
            else:
                ref = gen_ref("DOC")
                ts  = datetime.now().strftime("%d %B %Y, %I:%M %p")
                final_type   = d_type_other if d_type == "Other" else d_type
                urgent_label = "YES — within 24 hours" if d_urgent else "No"
                cc_list = parse_cc(d_cc)
                body = email_template(
                    "Document Request", ref,
                    {"Name": d_name, "Employee ID": d_id, "Email": d_email,
                     "Business Unit": d_bu, "Document Type": final_type,
                     "Purpose": d_purpose, "Urgent": urgent_label,
                     "Additional Details": d_comments or "None", "Submitted": ts},
                    "Standard documents issued within 3 working days. "
                    "Urgent requests within 24 hours.", cc_list
                )
                if send_email(f"[OrgX Document] {ref} — {final_type} | {d_name}",
                              body, cc_list):
                    log_to_sheet("Document Requests", [
                        ref, ts, d_name, d_id, d_email, d_bu,
                        final_type, d_purpose, urgent_label,
                        d_comments, ", ".join(cc_list), "Pending"
                    ])
                    st.session_state.docreq_done = True
                    st.session_state.docreq_ref  = ref
                    st.rerun()
                else:
                    st.error(f"Submission failed: "
                             f"{st.session_state.get('email_error','Unknown error')}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — GRIEVANCE
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Grievance Form")
    st.caption("All grievances are handled confidentially. No-retaliation policy applies.")
    st.divider()

    if st.session_state.grievance_done:
        success_block(st.session_state.grievance_ref, "Grievance")
        st.info("Your grievance will be acknowledged within **2 working days** "
                "and resolved within **15 working days** (Tier 2 policy).")
        if st.button("Submit another grievance"):
            st.session_state.grievance_done = False
            st.rerun()
    else:
        st.info("**Before proceeding:** Please attempt informal resolution with your "
                "reporting manager first (Tier 1), if safe and appropriate. Use this "
                "form if that was not possible or the grievance involves your manager.")

        st.markdown("#### Your Details")
        c1, c2 = st.columns(2)
        with c1:
            g_name  = st.text_input("Full Name *",   key="g_name")
            g_id    = st.text_input("Employee ID *", key="g_id")
            g_email = st.text_input("Work Email *",  key="g_email")
        with c2:
            g_bu   = st.selectbox("Business Unit *", BUS_UNITS,   key="g_bu")
            g_dept = st.selectbox("Department *",    DEPARTMENTS, key="g_dept")

        st.divider()
        st.markdown("#### Grievance Details")
        g_type = st.selectbox("Grievance Type *", [
            "Select...",
            "Workplace Conduct / Behaviour",
            "Unfair Treatment / Discrimination",
            "Harassment or Bullying",
            "Manager / Leadership Concern",
            "Appraisal or Compensation Dispute",
            "HR Process Concern",
            "Policy Violation",
            "POSH — Sexual Harassment",
            "Other"
        ], key="g_type")

        g_type_other = ""
        if g_type == "Other":
            g_type_other = st.text_input(
                "Please describe the type of grievance *",
                placeholder="Briefly describe the nature of your concern...",
                key="g_type_other")

        if g_type == "POSH — Sexual Harassment":
            st.warning("⚠️ For POSH complaints, please also email **posh-ic@orgx.com** "
                       "directly for immediate action under the POSH Act, 2013.")

        g_against = st.text_input(
            "Name or Role this concerns (optional)",
            placeholder="e.g. Reporting Manager, Team Lead",
            key="g_against")

        g_desc = st.text_area("Description of Grievance *", height=150,
            key="g_desc",
            placeholder="Please describe the concern in detail. Include dates, "
                        "locations, and any witnesses if applicable.")

        g_resolution = st.text_area("What outcome are you seeking? *",
            height=80, key="g_resolution",
            placeholder="e.g. Formal acknowledgement, mediation, disciplinary action...")

        g_tier1 = st.radio(
            "Have you attempted informal resolution with your manager? *",
            ["Yes — it was not resolved",
             "No — it was not safe or appropriate",
             "No — the grievance involves my manager directly"],
            key="g_tier1"
        )

        st.divider()
        st.markdown("**CC (optional)**")
        g_cc = st.text_input("Email address(es) to copy",
            placeholder="e.g. trusted.colleague@orgx.com",
            key="g_cc",
            help="Only add someone you explicitly want copied on this grievance.")

        st.divider()
        st.warning("⚠️ All information is strictly confidential and shared only with "
                   "those directly involved in resolution. OrgX's no-retaliation policy "
                   "protects all employees who raise grievances in good faith.")

        if st.button("Submit Grievance →", type="primary", key="grievance_submit"):
            errors = []
            if not g_name:        errors.append("Full Name")
            if not g_id:          errors.append("Employee ID")
            if not g_email:       errors.append("Work Email")
            if g_bu   == "Select...": errors.append("Business Unit")
            if g_dept == "Select...": errors.append("Department")
            if g_type == "Select...": errors.append("Grievance Type")
            if g_type == "Other" and not g_type_other:
                errors.append("Please describe the type of grievance")
            if not g_desc:        errors.append("Description")
            if not g_resolution:  errors.append("Desired Outcome")
            if errors:
                st.error(f"Please fill in: {', '.join(errors)}")
            else:
                ref = gen_ref("GRV")
                ts  = datetime.now().strftime("%d %B %Y, %I:%M %p")
                final_type = g_type_other if g_type == "Other" else g_type
                cc_list    = parse_cc(g_cc)
                body = email_template(
                    "Grievance Submitted — CONFIDENTIAL", ref,
                    {"Name": g_name, "Employee ID": g_id, "Email": g_email,
                     "Business Unit": g_bu, "Department": g_dept,
                     "Grievance Type": final_type,
                     "Concerns": g_against or "Not specified",
                     "Tier 1 Attempted": g_tier1,
                     "Description": g_desc,
                     "Desired Outcome": g_resolution, "Submitted": ts},
                    "CONFIDENTIAL. Acknowledge within 2 working days. Resolve within "
                    "15 working days (Tier 2). Share only with those directly involved.",
                    cc_list
                )
                if send_email(
                    f"[OrgX Grievance — CONFIDENTIAL] {ref} | {final_type}",
                    body, cc_list
                ):
                    log_to_sheet("Grievances", [
                        ref, ts, g_name, g_id, g_email, g_bu, g_dept,
                        final_type, g_against, g_tier1, g_desc,
                        g_resolution, ", ".join(cc_list), "Open"
                    ])
                    st.session_state.grievance_done = True
                    st.session_state.grievance_ref  = ref
                    st.rerun()
                else:
                    st.error(f"Submission failed: "
                             f"{st.session_state.get('email_error','Unknown error')}")

st.divider()
st.caption("OrgX HR Portal · All submissions are confidential and "
           "processed by the People & Culture team")
