import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import uuid
import google.generativeai as genai

st.set_page_config(
    page_title="OrgX HR Assistant",
    page_icon="🏢",
    layout="centered"
)

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

def send_email(emp_name, emp_email, emp_id, business_unit, query, ticket_id, gmail_user, gmail_password, recipient_email):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[OrgX HR Ticket] {ticket_id} - New Support Request"
        msg["From"] = gmail_user
        msg["To"] = recipient_email
        timestamp = datetime.now().strftime("%d %B %Y, %I:%M %p")
        body = f"""
        <html><body style="font-family:Arial,sans-serif;padding:20px;">
        <div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;border:1px solid #e0e0e0;">
        <div style="background:#1F4E79;padding:20px 30px;">
        <h2 style="color:white;margin:0;">OrgX HR Service Portal</h2>
        <p style="color:#BDD7EE;margin:4px 0 0;">New Support Ticket</p>
        </div>
        <div style="padding:25px 30px;">
        <p><b>Ticket ID:</b> {ticket_id}</p>
        <p><b>Name:</b> {emp_name}</p>
        <p><b>Employee ID:</b> {emp_id}</p>
        <p><b>Email:</b> {emp_email}</p>
        <p><b>Business Unit:</b> {business_unit}</p>
        <p><b>Submitted:</b> {timestamp}</p>
        <hr/>
        <p><b>Query:</b></p>
        <p style="background:#f0f4f8;padding:12px;border-radius:8px;">{query}</p>
        <hr/>
        <p style="color:#6b7280;font-size:0.85rem;">Please respond within 15 working days (Tier 2 policy).</p>
        </div></div>
        </body></html>
        """
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, recipient_email, msg.as_string())
        return True
    except Exception as e:
        st.session_state["email_error"] = str(e)
        return False

def get_gemini_response(user_messages, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-3.1-pro-preview",
        system_instruction=HR_POLICY_CONTEXT
    )
    history = []
    for msg in user_messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
    chat = model.start_chat(history=history)
    response = chat.send_message(user_messages[-1]["content"])
    return response.text

# Session state init
for key, val in [
    ("messages", []),
    ("show_ticket_form", False),
    ("ticket_raised", False),
    ("last_query", ""),
    ("ticket_id", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = val

# Sidebar
with st.sidebar:
    st.markdown("### Configuration")
    st.divider()
    api_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
    st.caption("Get your free key at aistudio.google.com → Get API Key")
    st.divider()
    gmail_user = st.text_input("Gmail (sender)", placeholder="yourname@gmail.com")
    gmail_password = st.text_input("Gmail App Password", type="password", placeholder="xxxx xxxx xxxx xxxx")
    recipient_email = st.text_input("P&C Team Email", placeholder="pc-team@orgx.com")
    st.divider()
    st.caption("Gmail App Password: myaccount.google.com > Security > App passwords")
    if st.button("Clear conversation"):
        for key in ["messages", "show_ticket_form", "ticket_raised", "last_query", "ticket_id"]:
            st.session_state[key] = [] if key == "messages" else (False if key in ["show_ticket_form", "ticket_raised"] else "")
        st.rerun()

# Header
st.title("OrgX HR Assistant")
st.caption("Ask me about leave, reimbursements, appraisals, payroll, or grievances.")
st.divider()

# Welcome message
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("""Hello! I am the OrgX HR Assistant. I can help you with:

- **Leave** — entitlements, carry-forward, sick leave, sabbatical
- **Reimbursements** — meals, travel, equipment
- **Appraisals** — process, eligibility, KRAs
- **Payroll** — payslips, salary structure, tax
- **Grievances** — how to raise a concern

What can I help you with today?""")

# Render conversation history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.write(msg["content"])
            if msg.get("escalation") and not msg.get("ticket_raised"):
                st.warning("This query is outside my knowledge base. Please raise a support ticket below.")
            if msg.get("ticket_raised"):
                st.success(f"Ticket {st.session_state.ticket_id} raised. The P&C team will respond within 15 working days.")

# Ticket form
if st.session_state.show_ticket_form and not st.session_state.ticket_raised:
    st.divider()
    st.subheader("Raise a Support Ticket")
    col1, col2 = st.columns(2)
    with col1:
        emp_name = st.text_input("Full Name *")
        emp_id = st.text_input("Employee ID *")
    with col2:
        emp_email = st.text_input("Work Email *")
        emp_bu = st.selectbox("Business Unit *", ["Select...", "Consumer Products", "Financial Services", "Technology Solutions", "Infrastructure", "Corporate Functions"])
    ticket_query = st.text_area("Your Query", value=st.session_state.last_query, height=80)
    col_a, col_b = st.columns([1, 4])
    with col_a:
        submit = st.button("Send Ticket", type="primary")
    with col_b:
        if st.button("Cancel"):
            st.session_state.show_ticket_form = False
            st.rerun()
    if submit:
        if not all([emp_name, emp_email, emp_id]) or emp_bu == "Select...":
            st.error("Please fill in all required fields.")
        elif not all([gmail_user, gmail_password, recipient_email]):
            st.error("Please fill in Gmail settings in the sidebar.")
        else:
            tid = f"TKT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
            st.session_state.ticket_id = tid
            ok = send_email(emp_name, emp_email, emp_id, emp_bu, ticket_query, tid, gmail_user, gmail_password, recipient_email)
            if ok:
                if st.session_state.messages:
                    st.session_state.messages[-1]["ticket_raised"] = True
                st.session_state.ticket_raised = True
                st.session_state.show_ticket_form = False
                st.rerun()
            else:
                err = st.session_state.get("email_error", "Unknown error")
                st.error(f"Email failed: {err}. Check Gmail credentials in sidebar.")

st.divider()

# Chat input
if not st.session_state.show_ticket_form:
    user_input = st.chat_input("Type your HR question here...")
    if user_input:
        if not api_key:
            st.error("Please enter your Gemini API key in the sidebar.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user", avatar="👤"):
            st.write(user_input)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                try:
                    response_text = get_gemini_response(st.session_state.messages, api_key)
                    st.write(response_text)

                    escalation_phrases = [
                        "don't have information",
                        "outside my current knowledge",
                        "raise a support ticket",
                        "i'm sorry, i don't have"
                    ]
                    needs_escalation = any(p in response_text.lower() for p in escalation_phrases)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "escalation": needs_escalation,
                        "ticket_raised": False
                    })

                    if needs_escalation:
                        st.warning("This query is outside my knowledge base. Please raise a support ticket below.")
                        st.session_state.show_ticket_form = True
                        st.session_state.ticket_raised = False
                        st.session_state.last_query = user_input
                        st.rerun()

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.messages.pop()

st.caption("OrgX HR Assistant · Powered by Gemini AI · For HR queries only")
