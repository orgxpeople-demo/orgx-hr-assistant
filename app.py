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

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .main {
        background-color: #F8F7F4;
    }

    .block-container {
        padding-top: 2rem;
        max-width: 780px;
    }

    .orgx-header {
        background: #1F4E79;
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        color: white;
    }

    .orgx-header h1 {
        font-family: 'DM Serif Display', serif;
        font-size: 2rem;
        font-weight: 400;
        margin: 0 0 0.25rem 0;
        color: white;
        letter-spacing: -0.5px;
    }

    .orgx-header p {
        font-size: 0.9rem;
        color: #BDD7EE;
        margin: 0;
        font-weight: 300;
    }

    .orgx-badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        color: #BDD7EE;
        font-size: 0.7rem;
        font-weight: 500;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        margin-bottom: 1rem;
    }

    .chat-container {
        background: white;
        border-radius: 16px;
        border: 1px solid #E8E4DC;
        padding: 1.5rem;
        min-height: 400px;
        max-height: 520px;
        overflow-y: auto;
        margin-bottom: 1rem;
    }

    .message-user {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 1rem;
    }

    .message-user .bubble {
        background: #1F4E79;
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 16px 16px 4px 16px;
        max-width: 75%;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    .message-bot {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        margin-bottom: 1rem;
    }

    .bot-avatar {
        width: 36px;
        height: 36px;
        min-width: 36px;
        background: #1F4E79;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: 600;
        color: white;
    }

    .message-bot .bubble {
        background: #F0F4F8;
        color: #1a1a2e;
        padding: 0.75rem 1rem;
        border-radius: 4px 16px 16px 16px;
        max-width: 80%;
        font-size: 0.9rem;
        line-height: 1.6;
        border: 1px solid #E8E4DC;
    }

    .escalation-card {
        background: #FFF8E1;
        border: 1px solid #FFD54F;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-top: 0.75rem;
        font-size: 0.875rem;
    }

    .escalation-card strong {
        color: #E65100;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: block;
        margin-bottom: 0.5rem;
    }

    .ticket-success {
        background: #E8F5E9;
        border: 1px solid #A5D6A7;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-top: 0.75rem;
        font-size: 0.875rem;
        color: #2E7D32;
    }

    .ticket-success strong {
        display: block;
        margin-bottom: 0.25rem;
        font-size: 0.95rem;
    }

    .stTextInput input {
        border-radius: 12px !important;
        border: 1.5px solid #E8E4DC !important;
        padding: 0.75rem 1rem !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.9rem !important;
        background: white !important;
    }

    .stTextInput input:focus {
        border-color: #1F4E79 !important;
        box-shadow: 0 0 0 3px rgba(31,78,121,0.1) !important;
    }

    .stButton button {
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        padding: 0.5rem 1.25rem !important;
        transition: all 0.2s !important;
    }

    .stButton button[kind="primary"] {
        background: #1F4E79 !important;
        border: none !important;
        color: white !important;
    }

    .stButton button[kind="primary"]:hover {
        background: #163d60 !important;
    }

    .sidebar-info {
        background: #EEF4FA;
        border-radius: 12px;
        padding: 1rem;
        font-size: 0.8rem;
        color: #4a5568;
        margin-bottom: 1rem;
    }

    .sidebar-info h4 {
        color: #1F4E79;
        font-size: 0.85rem;
        margin: 0 0 0.5rem 0;
    }

    div[data-testid="stForm"] {
        background: transparent;
        border: none;
        padding: 0;
    }

    .ticket-form {
        background: white;
        border-radius: 16px;
        border: 1px solid #E8E4DC;
        padding: 1.5rem;
        margin-top: 1rem;
    }

    .footer-text {
        text-align: center;
        font-size: 0.75rem;
        color: #9CA3AF;
        margin-top: 1.5rem;
        padding-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

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

Process: Self Review → Manager Review → Leadership Calibration → Finance and P&C Processing → Final Ratings and Increments announced.

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

IMPORTANT INSTRUCTIONS FOR YOU (the HR Assistant):
1. Answer ONLY based on the policies above. Do not guess or make up information.
2. Be warm, clear, and concise. Use plain language.
3. If a question is partially covered, answer what you can and flag what isn't covered.
4. If the question is completely outside the above policies, respond with exactly this format:
   "I'm sorry, I don't have information on that in my current knowledge base. [Brief reason]. I'd recommend raising a support ticket so our People & Culture team can assist you directly."
5. Always end with a helpful note about contacting pc@orgx.com or the HR portal if needed.
"""

def send_email_notification(employee_name, employee_email, employee_id, business_unit, query, ticket_id, gmail_user, gmail_password, recipient_email):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[OrgX HR Ticket] {ticket_id} — New Support Request"
        msg['From'] = gmail_user
        msg['To'] = recipient_email

        timestamp = datetime.now().strftime("%d %B %Y, %I:%M %p")

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #f8f7f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; border: 1px solid #e0e0e0;">
                <div style="background: #1F4E79; padding: 24px 32px;">
                    <h2 style="color: white; margin: 0; font-size: 1.4rem;">OrgX HR Service Portal</h2>
                    <p style="color: #BDD7EE; margin: 4px 0 0; font-size: 0.85rem;">New Support Ticket Raised</p>
                </div>
                <div style="padding: 28px 32px;">
                    <div style="background: #FFF3E0; border-left: 4px solid #FF9800; padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 24px;">
                        <strong style="color: #E65100; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px;">Ticket ID</strong>
                        <p style="margin: 4px 0 0; font-size: 1rem; font-weight: 600; color: #1a1a2e;">{ticket_id}</p>
                    </div>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
                        <tr style="border-bottom: 1px solid #f0f0f0;">
                            <td style="padding: 10px 0; color: #6b7280; font-size: 0.85rem; width: 140px;">Employee Name</td>
                            <td style="padding: 10px 0; font-weight: 500; font-size: 0.9rem;">{employee_name}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f0f0f0;">
                            <td style="padding: 10px 0; color: #6b7280; font-size: 0.85rem;">Employee ID</td>
                            <td style="padding: 10px 0; font-weight: 500; font-size: 0.9rem;">{employee_id}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f0f0f0;">
                            <td style="padding: 10px 0; color: #6b7280; font-size: 0.85rem;">Email</td>
                            <td style="padding: 10px 0; font-weight: 500; font-size: 0.9rem;">{employee_email}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f0f0f0;">
                            <td style="padding: 10px 0; color: #6b7280; font-size: 0.85rem;">Business Unit</td>
                            <td style="padding: 10px 0; font-weight: 500; font-size: 0.9rem;">{business_unit}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280; font-size: 0.85rem;">Submitted At</td>
                            <td style="padding: 10px 0; font-weight: 500; font-size: 0.9rem;">{timestamp}</td>
                        </tr>
                    </table>
                    <div style="background: #F0F4F8; border-radius: 8px; padding: 16px 20px;">
                        <p style="color: #6b7280; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 8px;">Employee Query</p>
                        <p style="margin: 0; font-size: 0.95rem; line-height: 1.6; color: #1a1a2e;">{query}</p>
                    </div>
                    <div style="margin-top: 24px; padding-top: 20px; border-top: 1px solid #f0f0f0;">
                        <p style="color: #6b7280; font-size: 0.8rem; margin: 0;">Please respond to this ticket within <strong>15 working days</strong> as per OrgX's Grievance Policy (Tier 2). Reply directly to the employee at <a href="mailto:{employee_email}" style="color: #1F4E79;">{employee_email}</a>.</p>
                    </div>
                </div>
                <div style="background: #f8f7f4; padding: 16px 32px; text-align: center;">
                    <p style="color: #9ca3af; font-size: 0.75rem; margin: 0;">OrgX HR Service Portal · Confidential · Do not forward</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, recipient_email, msg.as_string())

        return True
    except Exception as e:
        return False

def get_ai_response(messages, client):
    system_message = HR_POLICY_CONTEXT
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=system_message,
        messages=messages
    )
    return response.content[0].text

def is_escalation_needed(response_text):
    escalation_phrases = [
        "don't have information",
        "outside my current knowledge",
        "raise a support ticket",
        "not covered in my",
        "i'm sorry, i don't have"
    ]
    return any(phrase in response_text.lower() for phrase in escalation_phrases)

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
    st.markdown("### ⚙️ Configuration")
    st.markdown("---")

    st.markdown("**Anthropic API Key**")
    api_key = st.text_input("", type="password", placeholder="sk-ant-...", key="api_key", label_visibility="collapsed")

    st.markdown("**Gmail (sender)**")
    gmail_user = st.text_input("", placeholder="yourname@gmail.com", key="gmail_user", label_visibility="collapsed")

    st.markdown("**Gmail App Password**")
    gmail_password = st.text_input("", type="password", placeholder="xxxx xxxx xxxx xxxx", key="gmail_password", label_visibility="collapsed")

    st.markdown("**P&C Team Email (recipient)**")
    recipient_email = st.text_input("", placeholder="pc-team@orgx.com", key="recipient_email", label_visibility="collapsed")

    st.markdown("---")
    st.markdown("""
    <div class="sidebar-info">
    <h4>📋 How to get Gmail App Password</h4>
    1. Go to your Google Account<br>
    2. Security → 2-Step Verification (enable if off)<br>
    3. Search "App passwords"<br>
    4. Create one for "Mail"<br>
    5. Paste the 16-character code above
    </div>
    """, unsafe_allow_html=True)

    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.session_state.show_ticket_form = False
        st.session_state.ticket_raised = False
        st.session_state.last_unresolved_query = ""
        st.rerun()

st.markdown("""
<div class="orgx-header">
    <div class="orgx-badge">HR Self-Service</div>
    <h1>OrgX HR Assistant</h1>
    <p>Ask me anything about leave, reimbursements, appraisals, payroll, or grievances.</p>
</div>
""", unsafe_allow_html=True)

chat_html = '<div class="chat-container" id="chat-box">'

if not st.session_state.messages:
    chat_html += """
    <div class="message-bot">
        <div class="bot-avatar">HR</div>
        <div class="bubble">
            👋 Hello! I'm the OrgX HR Assistant. I can help you with questions about:<br><br>
            • <strong>Leave</strong> — entitlements, carry-forward, sick leave, sabbatical<br>
            • <strong>Reimbursements</strong> — meals, travel, equipment<br>
            • <strong>Appraisals</strong> — process, eligibility, KRAs<br>
            • <strong>Payroll</strong> — payslips, salary structure, tax<br>
            • <strong>Grievances</strong> — how to raise a concern<br><br>
            What can I help you with today?
        </div>
    </div>
    """

for msg in st.session_state.messages:
    if msg["role"] == "user":
        chat_html += f"""
        <div class="message-user">
            <div class="bubble">{msg["content"]}</div>
        </div>
        """
    else:
        content = msg["content"]
        chat_html += f"""
        <div class="message-bot">
            <div class="bot-avatar">HR</div>
            <div class="bubble">{content}</div>
        </div>
        """
        if msg.get("escalation"):
            chat_html += """
            <div class="escalation-card">
                <strong>⚠️ Escalation Required</strong>
                This query couldn't be resolved from the current knowledge base.
                Use the form below to raise a support ticket — the P&C team will respond within 15 working days.
            </div>
            """
        if msg.get("ticket_raised"):
            chat_html += f"""
            <div class="ticket-success">
                <strong>✅ Ticket Raised Successfully</strong>
                Ticket ID: <strong>{st.session_state.ticket_id}</strong><br>
                An email notification has been sent to the People & Culture team. You will hear back within 15 working days.
            </div>
            """

chat_html += '</div>'
st.markdown(chat_html, unsafe_allow_html=True)

if st.session_state.show_ticket_form and not st.session_state.ticket_raised:
    st.markdown("---")
    st.markdown("#### 📝 Raise a Support Ticket")
    st.markdown("Fill in your details below and we'll notify the People & Culture team.")

    col1, col2 = st.columns(2)
    with col1:
        emp_name = st.text_input("Full Name *", placeholder="e.g. Priya Sharma")
        emp_id = st.text_input("Employee ID *", placeholder="e.g. EMP-1042")
    with col2:
        emp_email = st.text_input("Work Email *", placeholder="e.g. priya.sharma@orgx.com")
        emp_bu = st.selectbox("Business Unit *", [
            "Select...",
            "Consumer Products",
            "Financial Services",
            "Technology Solutions",
            "Infrastructure",
            "Corporate Functions"
        ])

    st.text_area("Your Query", value=st.session_state.last_unresolved_query, key="ticket_query", height=100)

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        submit = st.button("Send Ticket →", type="primary", use_container_width=True)
    with col_btn2:
        cancel = st.button("Cancel", use_container_width=False)

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
            query_text = st.session_state.get("ticket_query", st.session_state.last_unresolved_query)

            success = send_email_notification(
                employee_name=emp_name,
                employee_email=emp_email,
                employee_id=emp_id,
                business_unit=emp_bu,
                query=query_text,
                ticket_id=ticket_id,
                gmail_user=gmail_user,
                gmail_password=gmail_password,
                recipient_email=recipient_email
            )

            if success:
                st.session_state.messages[-1]["ticket_raised"] = True
                st.session_state.ticket_raised = True
                st.session_state.show_ticket_form = False
                st.success(f"✅ Ticket {ticket_id} raised! Email sent to the P&C team.")
                st.rerun()
            else:
                st.error("Email failed to send. Please check your Gmail credentials in the sidebar and try again.")

st.markdown("---")

if not st.session_state.show_ticket_form:
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input(
                "Message",
                placeholder="Ask me about leave, payroll, appraisals...",
                label_visibility="collapsed"
            )
        with col2:
            submitted = st.form_submit_button("Send →", type="primary", use_container_width=True)

    if submitted and user_input.strip():
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
                st.error(f"Error connecting to AI: {str(e)}")

            st.rerun()

st.markdown("""
<div class="footer-text">
    OrgX HR Assistant · Powered by Claude AI · For HR queries only · Not a substitute for official HR advice
</div>
""", unsafe_allow_html=True)
