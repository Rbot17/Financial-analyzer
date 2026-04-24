
import streamlit as st
import anthropic
import requests

st.set_page_config(page_title="Financial Analyzer", page_icon="📊", layout="wide")

# ── Header ─────────────────────────────────────────────────
st.title("📊 Financial Analyzer")
st.write("Analyze company financials using SEC EDGAR data and your own documents.")

# ── Sidebar ────────────────────────────────────────────────
st.sidebar.header("⚙️ Settings")
api_key = st.sidebar.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")

st.sidebar.header("📂 Data Source")
mode = st.sidebar.radio(
    "Choose how to load data:",
    ["Upload My Own Documents", "Fetch SEC EDGAR Data", "Both"]
)

# ── State Variables ────────────────────────────────────────
if "balance_text" not in st.session_state:
    st.session_state.balance_text = "No balance sheet loaded."
if "metrics_text" not in st.session_state:
    st.session_state.metrics_text = "No metrics calculated."
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = ""

# ── Document Upload ────────────────────────────────────────
if mode in ["Upload My Own Documents", "Both"]:
    st.header("📄 Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload your financial documents",
        accept_multiple_files=True,
        type=["txt", "csv"]
    )
    if uploaded_files:
        documents = {}
        for f in uploaded_files:
            documents[f.name] = f.read().decode("utf-8")
            st.success(f"✓ Loaded: {f.name}")
        st.session_state.knowledge_base = "\n\n".join([
            f"--- {name} ---\n{text}"
            for name, text in documents.items()
        ])

# ── SEC EDGAR ──────────────────────────────────────────────
if mode in ["Fetch SEC EDGAR Data", "Both"]:
    st.header("🏢 SEC EDGAR Balance Sheet")

    ticker = st.text_input(
        "Enter Stock Ticker",
        placeholder="e.g. AAPL, TSLA, MSFT"
    ).strip().upper()

    if ticker and st.button("📥 Load Balance Sheet"):
        with st.spinner(f"Fetching data for {ticker} from SEC EDGAR..."):
            try:
                headers = {"User-Agent": "student-project student@email.com"}
                cik_lookup = requests.get(
                    "https://www.sec.gov/files/company_tickers.json",
                    headers=headers
                ).json()

                cik = None
                company_name = ""
                for key, val in cik_lookup.items():
                    if val["ticker"] == ticker:
                        cik = str(val["cik_str"]).zfill(10)
                        company_name = val["title"]
                        break

                if not cik:
                    st.error(f"Ticker {ticker} not found. Please check and try again.")
                else:
                    facts = requests.get(
                        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                        headers=headers
                    ).json()

                    def get_val(concept):
                        try:
                            units = facts["facts"]["us-gaap"][concept]["units"]["USD"]
                            annual = [x for x in units if x.get("form") == "10-K"]
                            return annual[-1]["val"] if annual else None
                        except:
                            return None

                    def fmt(val):
                        return f"${val:,.0f}" if val is not None else "N/A"

                    def safe_div(a, b):
                        try:
                            return float(a) / float(b) if b and float(b) != 0 else None
                        except:
                            return None

                    total_assets      = get_val("Assets")
                    total_liabilities = get_val("Liabilities")
                    total_equity      = get_val("StockholdersEquity")
                    current_assets    = get_val("AssetsCurrent")
                    current_liab      = get_val("LiabilitiesCurrent")
                    cash              = get_val("CashAndCashEquivalentsAtCarryingValue")
                    inventory         = get_val("InventoryNet")
                    receivables       = get_val("AccountsReceivableNetCurrent")
                    ppe               = get_val("PropertyPlantAndEquipmentNet")
                    goodwill          = get_val("Goodwill")
                    retained_earnings = get_val("RetainedEarningsAccumulatedDeficit")
                    long_term_debt    = get_val("LongTermDebt")
                    accounts_payable  = get_val("AccountsPayableCurrent")
                    short_term_debt   = get_val("ShortTermBorrowings")

                    # ── Filing Date ────────────────────────────────
                    try:
                        annual_filings = [x for x in facts["facts"]["us-gaap"]["Assets"]["units"]["USD"] if x.get("form") == "10-K"]
                        latest = annual_filings[-1]
                        filing_date = latest["end"]
                    except:
                        filing_date = "Unknown"

                    st.success(f"✓ Loaded: {company_name} ({ticker}) — Filing date: {filing_date}")

                    # ── Balance Sheet Display ──────────────────────
                    st.subheader(f"Balance Sheet — {company_name} ({ticker})")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("### 🏦 Assets")
                        st.write(f"**Cash & Equivalents:** {fmt(cash)}")
                        st.write(f"**Net Receivables:** {fmt(receivables)}")
                        st.write(f"**Inventory:** {fmt(inventory)}")
                        st.write(f"**Current Assets:** {fmt(current_assets)}")
                        st.write(f"**PP&E:** {fmt(ppe)}")
                        st.write(f"**Goodwill:** {fmt(goodwill)}")
                        st.metric("Total Assets", fmt(total_assets))

                    with col2:
                        st.markdown("### 💳 Liabilities")
                        st.write(f"**Accounts Payable:** {fmt(accounts_payable)}")
                        st.write(f"**Short-Term Debt:** {fmt(short_term_debt)}")
                        st.write(f"**Current Liabilities:** {fmt(current_liab)}")
                        st.write(f"**Long-Term Debt:** {fmt(long_term_debt)}")
                        st.metric("Total Liabilities", fmt(total_liabilities))

                    with col3:
                        st.markdown("### 💰 Equity")
                        st.write(f"**Retained Earnings:** {fmt(retained_earnings)}")
                        st.metric("Total Equity", fmt(total_equity))

                    # ── Metrics Display ────────────────────────────
                    st.subheader("📈 Key Financial Metrics")
                    m1, m2, m3, m4 = st.columns(4)

                    current_ratio = safe_div(current_assets, current_liab)
                    dte           = safe_div(total_liabilities, total_equity)
                    equity_ratio  = safe_div(total_equity, total_assets)
                    cash_ratio    = safe_div(cash, current_liab)
                    working_cap   = (current_assets or 0) - (current_liab or 0)

                    m1.metric("Current Ratio",  f"{current_ratio:.2f}x" if current_ratio else "N/A")
                    m2.metric("Debt-to-Equity", f"{dte:.2f}x"           if dte           else "N/A")
                    m3.metric("Equity Ratio",   f"{equity_ratio:.2f}x"  if equity_ratio  else "N/A")
                    m4.metric("Cash Ratio",     f"{cash_ratio:.2f}x"    if cash_ratio    else "N/A")
                    st.metric("Working Capital", fmt(working_cap))

                    # ── Save to session state for Claude ───────────
                    st.session_state.balance_text = f"""
Company: {company_name} ({ticker})
Filing Date: {filing_date}
Total Assets: {fmt(total_assets)}
Total Liabilities: {fmt(total_liabilities)}
Total Equity: {fmt(total_equity)}
Current Assets: {fmt(current_assets)}
Current Liabilities: {fmt(current_liab)}
Cash: {fmt(cash)}
Inventory: {fmt(inventory)}
Long-Term Debt: {fmt(long_term_debt)}
Retained Earnings: {fmt(retained_earnings)}
"""
                    st.session_state.metrics_text = f"""
Current Ratio: {f"{current_ratio:.2f}" if current_ratio else "N/A"}
Debt-to-Equity: {f"{dte:.2f}" if dte else "N/A"}
Equity Ratio: {f"{equity_ratio:.2f}" if equity_ratio else "N/A"}
Cash Ratio: {f"{cash_ratio:.2f}" if cash_ratio else "N/A"}
Working Capital: {fmt(working_cap)}
"""

            except Exception as e:
                st.error(f"Error fetching data: {e}")

# ── Ask Questions ─────────────────────────────────────────────
st.header("Ask Questions")
your_question = st.text_input(
    "Type your question:",
    placeholder="e.g. Is this company financially healthy?"
)

if st.button("🔍 Analyze"):
    if not api_key:
        st.error("Please enter your Anthropic API key in the sidebar.")
    elif not your_question:
        st.warning("Please type a question first.")
    else:
        with st.spinner("Analyzing..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=500,
                    messages=[
                        {
                            "role": "user",
                            "content": f"""You are a financial analyst.

BALANCE SHEET:
{st.session_state.balance_text}

CALCULATED METRICS:
{st.session_state.metrics_text}

UPLOADED DOCUMENTS:
{st.session_state.knowledge_base[:3000] if st.session_state.knowledge_base else "No documents uploaded."}

Answer this question clearly:
{your_question}"""
                        }
                    ]
                )
                st.success("✅ Claude says:")
                st.write(message.content[0].text)

            except Exception as e:
                st.error(f"Claude error: {e}")

# ── Footer ─────────────────────────────────────────────────
st.divider()
st.caption("⚠️ This tool is for educational purposes only and does not constitute financial advice.")
