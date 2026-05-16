import streamlit as st
import anthropic
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import uuid

st.set_page_config(
    page_title="OrgX HR Assistant",
    page_icon="🏢",
    layout="centered"
)

HR_POLICY_CONTEXT = """
You are the OrgX HR Assistant — an AI-powered self-service tool for OrgX employees.
You answer questions based ONLY on the following OrgX HR policies. If a question is outside
these policies, you must say so clearly and offer to raise a support ticket.

---

POLICY 1: LEAVE POLICY

Confirmed employees get 24 days paid leave per year. Employees on probation (first 6 months) get 2 days per month; remaining days credited upon confirmation.

Sick Leave: 12 days per year for all employees. Doctor's note required for absences over 3 consecutive days.

Public Holidays: 8 fixed holidays per year, same across Delhi, Mumbai, Bangalore, Chennai, Hyderabad.

Sabbatical: After 5 years service, employees may take up to 3 months unpaid sabbatical. 6 months notice required. 3-year cooling-off period before next sabbatical.

Leave Carry Forward: Maximum 6 days can be carried forward. No leave encashment during employment.

Comp Off: Full day if worked 6+ hours on non-working day. Half day if worked 4-6 hours. Must be used within 1 month. Manager approval required.

Pro-Rated Leave (First Month):
- Joining 1st-15th: 1.5 days
- Joining 16th-25th: 1 day
- Joining 26th-31st: 0 days

All leaves must be applied via the HRMS portal.

---

POLICY 2: REIMBURSEMENT POLICY

Meal reimbursement: INR 500 per meal, up to 3 meals per day when travelling for work. Original bills required.

Local conveyance: Not reimbursable for daily commute. Reimbursed on actuals when travelling for official work.

Work equipment: Confirmed employees can claim up to INR 10,000 per year for work-related equipment (mouse, headphones, keyboard, webcam etc.). Receipt required. Claim within 30 days of purchase.

Manager team meals: Managers get INR 10,000 per quarter for team meals. Bills required. Does not carry forward.

All claims submitted via HRMS portal. Approved within 5 working days, paid in next month's salary.

---

POLICY 3: PERFORMANCE APPRAISAL

Appraisal cycle runs in January each year. Ratings and increments announced by end of February. Increments effective 1st April.

Eligibility: Must have completed 12 months service by 1st October of the appraisal year. Probationary employees are not eligible.

Process: Self Review > Manager Review > Leadership Calibration > Finance and P&C Processing > Final Ratings and Increments announced.

KRAs must be set with manager within 30 days of joining or start of performance year.

Rating scale: 1 (Does Not Meet) to 5 (Exceptional).

---

POLICY 4: PAYROLL AND PAYSLIP

Salary credited on or before last working day of each month.

Salary structure includes: Basic (40-50% of CTC), HRA (40-50% of Basic), Special Allowance, PF deduction (12% of Basic, capped at INR 1,800/month), Professional Tax, TDS.

Payslips available on HRMS portal by 5th of following month. Password: date of birth in DDMMYYYY format.

Tax declaration: Must be submitted at start of financial year (April). Investment proofs submitted January-February. OrgX supports Old and New Tax Regime. Regime cannot be changed mid-year.

Full and Final settlement processed within 45 days of last working day.

PF/UAN number available on payslip and HRMS portal under My Documents.

---

POLICY 5: GRIEVANCE AND ESCALATION

Tier 1 (Informal): Speak with reporting manager. If grievance involves manager, contact next level or P&C team. Resolve within 5 working days.

Tier 2 (Formal): Email pc@orgx.com or raise ticket on HR Service Portal. Acknowledged within 2 working days. Resolved within 15 working days.

Tier 3 (Senior Escalation): Email headpc@orgx.com within 5 working days of Tier 2 outcome. Final resolution within 10 working days.

POSH complaints: Contact Internal Committee at posh-ic@orgx.com. Handled confidentially under POSH Act 2013.

No retaliation policy. All grievances handled confidentially.

---

IMPORTANT INSTRUCTIONS:
1. Answer ONLY based on the policies above. Do not guess or make up information.
2. Be warm, clear, and concise. Use plain language.
3. If a question is partially covered, answer what you can and flag what is not covered.
4. If the question is completely outside the above policies, respond with:
   "I'm sorry, I don't have information on that in my current knowledge base. I'd recommend raising a support ticket so our People & Culture team can assist you directly."
5. Always end with a helpful note about contacting pc@orgx.com or the HR portal if needed.
"""

def send_email_notification(employee_name, employee_email, employee_id, business_unit, query, ticket_id, gmail_user, gmail_password, recipient_email):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[OrgX HR Ticket] {ticket_id} - New Support Request"
        msg["From"] = gmail_user
        msg["To"] = recipient_email
        timestamp = datetime.now().strftime("%d %B %Y, %I:%M %p")
        html_body = f"""
        <html><body style="font-family: Arial, sans-serif; background: #f8f7f4; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; border: 1px solid #e0e0e0;">
            <div style="background: #1F4E79; padding: 24px 32px;">
                <h2 style="color: white; margin: 0;">OrgX HR Service Portal</h2>
                <p style="color: #BDD7EE; margin: 4px 0 0; font-size: 0.85rem;">New Support Ticket Raised</p>
            </div>
            <div style="padding: 28px 32px;">
                <p><strong>Ticket ID:</strong> {ticket_id}</p>
                <p><strong>Employee Name:</strong> {employee_name}</p>
                <p><strong>Employee ID:</strong> {employee_id}</p>
                <p><strong>Email:</strong> {employee_email}</p>
                <p><strong>Business Unit:</strong> {business_unit}</p>
                <p><strong>Submitted At:</strong> {timestamp}</p>
                <hr/>
                <p><strong>Query:</strong></p>
                <p style="background: #f0f4f8; padding: 12px; border-radius: 8px;">{query}</p>
                <hr/>
                <p style="color: #6b7280; font-size: 0.85rem;">Please respond within 15 working days as per OrgX Grievance Policy (Tier 2).</p>
            </div>
        </div>
        </body></html>
        """
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, recipient_email, msg.as_string())
        return True
    except Exception as e:
        return False

def get_ai_response(messages, client):
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=HR_POLICY_CONTEXT,
        messages=messages
    )
    return response.content[0].text

def is_escalation_needed(response_text):
    phrases = [
        "don't have information",
        "outside my current knowledge",
        "raise a support ticket",
        "not covered in my",
        "i'm sorry, i don't have"
    ]
    return any(p in response_text.lower() for p in phrases)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_ticket_form" not in st.session_state:
    st.session_state.show_ticket_form = False
if "ticket_raised" not in st.session_state:
    st.session_state.ticket_raised = False
if "last_unresolved_query" not in st.session_state:
    st.session_state.last_unresolved_query = ""
if "ticket_id" not in st.session_state:
    st.session_state.ticket_id = ""

with st.sidebar:
    st.markdown("### Configuration")
    st.divider()
    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
    gmail_user = st.text_input("Gmail (sender)", placeholder="yourname@gmail.com")
    gmail_password = st.text_input("Gmail App Password", type="password", placeholder="xxxx xxxx xxxx xxxx")
    recipient_email = st.text_input("P&C Team Email (recipient)", placeholder="pc-team@orgx.com")
    st.divider()
    st.caption("How to get Gmail App Password: Go to myaccount.google.com > Security > App passwords > Create one named OrgX Demo.")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.session_state.show_ticket_form = False
        st.session_state.ticket_raised = False
        st.session_state.last_unresolved_query = ""
        st.rerun()

st.title("OrgX HR Assistant")
st.caption("Ask me anything about leave, reimbursements, appraisals, payroll, or grievances.")
st.divider()

if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("""
Hello! I am the OrgX HR Assistant. I can help you with:

- **Leave** — entitlements, carry-forward, sick leave, sabbatical
- **Reimbursements** — meals, travel, equipment
- **Appraisals** — process, eligibility, KRAs
- **Payroll** — payslips, salary structure, tax
- **Grievances** — how to raise a concern

What can I help you with today?
        """)

for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(msg["content"])
            if msg.get("escalation"):
                st.warning("This query could not be resolved from the current knowledge base. Please use the form below to raise a support ticket — the P&C team will respond within 15 working days.")
            if msg.get("ticket_raised"):
                st.success(f"Ticket raised successfully! Ticket ID: {st.session_state.ticket_id}. The P&C team has been notified and will respond within 15 working days.")

if st.session_state.show_ticket_form and not st.session_state.ticket_raised:
    st.divider()
    st.subheader("Raise a Support Ticket")
    col1, col2 = st.columns(2)
    with col1:
        emp_name = st.text_input("Full Name *", placeholder="e.g. Priya Sharma")
        emp_id = st.text_input("Employee ID *", placeholder="e.g. EMP-1042")
    with col2:
        emp_email = st.text_input("Work Email *", placeholder="e.g. priya.sharma@orgx.com")
        emp_bu = st.selectbox("Business Unit *", ["Select...", "Consumer Products", "Financial Services", "Technology Solutions", "Infrastructure", "Corporate Functions"])
    ticket_query = st.text_area("Your Query", value=st.session_state.last_unresolved_query, height=100)
    col_a, col_b = st.columns([1, 3])
    with col_a:
        submit = st.button("Send Ticket", type="primary", use_container_width=True)
    with col_b:
        cancel = st.button("Cancel")
    if cancel:
        st.session_state.show_ticket_form = False
        st.rerun()
    if submit:
        if not emp_name or not emp_email or not emp_id or emp_bu == "Select...":
            st.error("Please fill in all required fields.")
        elif not gmail_user or not gmail_password or not recipient_email:
            st.error("Please configure Gmail settings in the sidebar before sending.")
        else:
            ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
            st.session_state.ticket_id = ticket_id
            success = send_email_notification(
                employee_name=emp_name,
                employee_email=emp_email,
                employee_id=emp_id,
                business_unit=emp_bu,
                query=ticket_query,
                ticket_id=ticket_id,
                gmail_user=gmail_user,
                gmail_password=gmail_password,
                recipient_email=recipient_email
            )
            if success:
                st.session_state.messages[-1]["ticket_raised"] = True
                st.session_state.ticket_raised = True
                st.session_state.show_ticket_form = False
                st.rerun()
            else:
                st.error("Email failed to send. Please check your Gmail credentials in the sidebar.")

st.divider()

if not st.session_state.show_ticket_form:
    user_input = st.chat_input("Ask me about leave, payroll, appraisals...")
    if user_input and user_input.strip():
        if not api_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
        else:
            st.session_state.messages.append({"role": "user", "content": user_input})
            try:
                client = anthropic.Anthropic(api_key=api_key)
                api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                response = get_ai_response(api_messages, client)
                needs_escalation = is_escalation_needed(response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "escalation": needs_escalation,
                    "ticket_raised": False
                })
                if needs_escalation:
                    st.session_state.show_ticket_form = True
                    st.session_state.ticket_raised = False
                    st.session_state.last_unresolved_query = user_input
            except Exception as e:
                st.error(f"Error: {str(e)}")
            st.rerun()

st.caption("OrgX HR Assistant · Powered by Claude AI · For HR queries only")
