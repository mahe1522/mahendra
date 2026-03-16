# ============================================
# RUN DHAN DASHBOARD
# ============================================

from dhan_dashboard import DhanTradingDashboard
from config import CLIENT_ID, ACCESS_TOKEN, MAX_LOSS, TARGET, RISK

print("\n" + "🚀"*50)
print("🚀  Starting Dhan Trading Dashboard...  🚀".center(50))
print("🚀"*50 + "\n")

dashboard = DhanTradingDashboard(
    client_id=CLIENT_ID,
    access_token=ACCESS_TOKEN,
    max_loss=MAX_LOSS,
    target=TARGET,
    risk=RISK
)

dashboard.run()