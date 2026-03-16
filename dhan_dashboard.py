# ============================================
# DHAN TRADING DASHBOARD - OPTION BUYER SPECIAL
# ============================================

from dhanhq import dhanhq
import time
from datetime import datetime, date
import sys
import os

class DhanTradingDashboard:
    def __init__(self, client_id, access_token, max_loss, target, risk):
        self.dhan = dhanhq(client_id, access_token)
        
        # OPTION BUYER SETTINGS
        self.MAX_LOSS = max_loss          # -2500
        self.TARGET = target               # 10000
        self.RISK = risk                   # 1500
        
        # Tracking variables
        self.kill_switch_activated = False
        self.dhan_kill_switch_active = False
        self.highest_pnl = 0
        self.trailing_stop = 0
        self.last_reset_date = date.today()
        
        # Trade statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # P&L tracking
        self.total_pnl = 0
        self.today_pnl = 0
        self.current_balance = 0
        self.start_balance = 0
        
        self.print_header()
        self.get_initial_data()
    
    def print_header(self):
        """Show header"""
        print("\n" + "="*120)
        print("📊  DHAN OPTION BUYER DASHBOARD - REAL TIME P&L MONITOR  📊".center(120))
        print("="*120)
        print(f"🎯 MAX LOSS: ₹{self.MAX_LOSS} | TARGET: ₹{self.TARGET} | TRAILING RISK: ₹{self.RISK}")
        print("⚠️  OPTION BUYER MODE - ONLY OPTIONS POSITIONS WILL BE TRACKED")
        print("-"*120)
    
    def get_initial_data(self):
        """Initial data fetch"""
        try:
            funds = self.dhan.get_fund_limits()
            if funds and funds.get('status') == 'success':
                data = funds.get('data', {})
                self.start_balance = float(data.get('availabelBalance', 0) or 0)
                self.current_balance = self.start_balance
        except Exception as e:
            pass
    
    def get_option_positions(self):
        """Get ONLY OPTIONS positions (no futures)"""
        try:
            positions = self.dhan.get_positions()
            option_positions = []
            
            if not positions or positions.get('status') != 'success':
                return []
            
            for pos in positions.get('data', []):
                exchange = str(pos.get('exchangeSegment', '')).upper()
                security_id = str(pos.get('securityId', '')).upper()
                
                # Check if it's an OPTION (CE/PE)
                is_option = False
                if 'CE' in security_id or 'PE' in security_id:
                    is_option = True
                if 'OPTION' in str(pos.get('instrumentType', '')).upper():
                    is_option = True
                if ('FNO' in exchange or exchange in ['NSE_FNO', 'BSE_FNO']) and is_option:
                    option_positions.append(pos)
            
            return option_positions
        except Exception as e:
            return []
    
    def calculate_pnl_from_positions(self, positions):
        """Calculate P&L from options positions"""
        total = 0.0
        for pos in positions:
            realized = float(pos.get('realizedProfit', 0) or 0)
            unrealized = float(pos.get('unrealizedProfit', 0) or 0)
            total += (realized + unrealized)
        return total
    
    def get_trade_statistics(self):
        """Get today's trade statistics"""
        try:
            today = date.today().strftime('%Y-%m-%d')
            trades = self.dhan.get_trade_history(
                from_date=today,
                to_date=today,
                page_number=0
            )
            
            win = 0
            loss = 0
            total_pnl_today = 0.0
            
            if trades and trades.get('status') == 'success':
                for trade in trades.get('data', []):
                    realized = float(trade.get('realizedProfit', 0) or 0)
                    total_pnl_today += realized
                    if realized > 0:
                        win += 1
                    elif realized < 0:
                        loss += 1
            
            return {
                'today_pnl': total_pnl_today,
                'winning_trades': win,
                'losing_trades': loss,
                'total_trades': win + loss
            }
        except Exception as e:
            return {
                'today_pnl': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_trades': 0
            }
    
    def get_balance_info(self):
        """Get current balance"""
        try:
            funds = self.dhan.get_fund_limits()
            if funds and funds.get('status') == 'success':
                data = funds.get('data', {})
                balance = float(data.get('availabelBalance', 0) or 0)
                self.current_balance = balance
                return balance
        except Exception as e:
            return self.current_balance if self.current_balance else 0
    
    def check_kill_switch_status(self):
        """Check Dhan Kill Switch status"""
        try:
            result = self.dhan.get_kill_switch_status()
            if result and result.get('status') == 'success':
                self.dhan_kill_switch_active = result.get('data', {}).get('isActive', False)
                return self.dhan_kill_switch_active
        except Exception as e:
            return False
    
    def calculate_exit_conditions(self, current_pnl):
        """OPTION BUYER exit conditions"""
        
        # Update highest PNL
        if current_pnl > self.highest_pnl:
            self.highest_pnl = current_pnl
        
        # OPTION BUYER trailing stop (more aggressive)
        if current_pnl >= self.TARGET:
            new_stop = self.highest_pnl - self.RISK
            if new_stop > self.trailing_stop:
                self.trailing_stop = new_stop
        
        # Check for time decay exit (last 30 minutes)
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        # Market close exit for options
        if current_hour == 15 and current_minute >= 20:
            return f"MARKET CLOSE EXIT - {current_hour}:{current_minute}"
        
        # Exit conditions
        if current_pnl <= self.MAX_LOSS:
            return f"MAX LOSS: ₹{current_pnl}"
        elif self.trailing_stop > 0 and current_pnl <= self.trailing_stop:
            return f"TRAILING STOP: ₹{current_pnl}"
        elif current_pnl >= self.TARGET and self.trailing_stop == 0:
            return f"TARGET HIT: ₹{current_pnl}"
        
        return None
    
    def exit_all_option_positions(self):
        """Exit ONLY options positions"""
        print("\n" + "🔄"*60)
        print("🔄 CLOSING ALL OPTIONS POSITIONS...")
        
        positions = self.get_option_positions()
        
        if not positions:
            print("📊 No Options positions to close")
            return True
        
        closed = 0
        for pos in positions:
            try:
                security_id = pos.get('securityId', 'Unknown')
                buy_qty = float(pos.get('buyQty', 0) or 0)
                sell_qty = float(pos.get('sellQty', 0) or 0)
                net_qty = buy_qty - sell_qty
                
                if abs(net_qty) > 0:
                    tx_type = "SELL" if net_qty > 0 else "BUY"
                    
                    # MARKET order for quick exit
                    order = self.dhan.place_order(
                        security_id=security_id,
                        exchange_segment=pos.get('exchangeSegment', 'NSE_FNO'),
                        transaction_type=tx_type,
                        quantity=int(abs(net_qty)),
                        order_type="MARKET",
                        product_type="INTRADAY",
                        price=0
                    )
                    
                    if order and order.get('status') == 'success':
                        closed += 1
                        print(f"   ✅ Closed Option: {security_id} - {abs(net_qty)} Qty")
                    else:
                        print(f"   ❌ Failed: {security_id}")
                    
                    time.sleep(0.3)  # Faster for options
            except Exception as e:
                print(f"   ❌ Error closing {security_id}: {e}")
        
        print(f"✅ Total {closed} Options positions closed")
        return True
    
    def activate_dhan_kill_switch(self):
        """Activate Dhan Kill Switch"""
        try:
            result = self.dhan.manage_kill_switch({"status": "ACTIVATE"})
            time.sleep(2)
            if self.check_kill_switch_status():
                print("\n" + "🔴"*60)
                print("🔴🔴🔴  DHAN KILL SWITCH ACTIVATED!  🔴🔴🔴")
                print("🔴"*60)
                print("⛔ No new orders will be placed today")
                return True
        except Exception as e:
            print(f"❌ Kill Switch Error: {e}")
            return False
    
    def reset_if_new_day(self):
        """Reset daily variables"""
        today = date.today()
        if today != self.last_reset_date:
            self.highest_pnl = 0
            self.trailing_stop = 0
            self.kill_switch_activated = False
            self.last_reset_date = today
            return True
        return False
    
    def display_dashboard(self):
        """Main dashboard display"""
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Get fresh data
        option_positions = self.get_option_positions()
        current_pnl = self.calculate_pnl_from_positions(option_positions)
        trade_stats = self.get_trade_statistics()
        balance = self.get_balance_info()
        self.check_kill_switch_status()
        
        # Update tracking
        if current_pnl > self.highest_pnl:
            self.highest_pnl = current_pnl
        
        # Trailing stop calculation
        if current_pnl >= self.TARGET and self.trailing_stop == 0:
            self.trailing_stop = self.highest_pnl - self.RISK
        elif current_pnl >= self.TARGET:
            new_stop = self.highest_pnl - self.RISK
            if new_stop > self.trailing_stop:
                self.trailing_stop = new_stop
        
        # Dashboard Header
        print("="*120)
        print(f"📊  OPTION BUYER DASHBOARD - {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        print("="*120)
        
        # BALANCE & P&L
        print(f"\n💰 BALANCE & P&L")
        print("-"*120)
        
        safe_balance = balance if balance is not None else 0
        safe_start = self.start_balance if self.start_balance is not None else 0
        safe_today = trade_stats['today_pnl'] if trade_stats['today_pnl'] is not None else 0
        safe_pnl = current_pnl if current_pnl is not None else 0
        
        print(f"   Current Balance: ₹{safe_balance:>15,.2f}   |   Today's P&L: ₹{safe_today:>15,.2f}")
        print(f"   Start Balance:   ₹{safe_start:>15,.2f}   |   Total P&L:    ₹{safe_pnl:>15,.2f}")
        
        # TRADE STATISTICS
        print(f"\n📊 TRADE STATISTICS (Today)")
        print("-"*120)
        
        safe_win = 0 if trade_stats['winning_trades'] is None else trade_stats['winning_trades']
        safe_loss = 0 if trade_stats['losing_trades'] is None else trade_stats['losing_trades']
        safe_total = safe_win + safe_loss
        win_rate = (safe_win / safe_total * 100) if safe_total > 0 else 0
        
        print(f"   Total Trades: {safe_total:>4}   |   Winning: {safe_win:>4}   |   Losing: {safe_loss:>4}   |   Win Rate: {win_rate:>6.1f}%")
        
        # KILL SWITCH & EXIT POINTS
        print(f"\n🔴 KILL SWITCH & EXIT POINTS")
        print("-"*120)
        ks_status = "🔴 ACTIVE" if self.dhan_kill_switch_active else "🟢 INACTIVE"
        ks_reason = " (Triggered by system)" if self.kill_switch_activated else ""
        print(f"   Kill Switch Status: {ks_status}{ks_reason}")
        print(f"   Highest P&L Today: ₹{self.highest_pnl:>15,.2f}")
        
        exit_point = self.trailing_stop if self.trailing_stop > 0 else self.TARGET
        exit_type = "Trailing Stop" if self.trailing_stop > 0 else "Initial Target"
        print(f"   Exit Point: ₹{exit_point:>15,.2f} ({exit_type})")
        
        # Check for market close
        now = datetime.now()
        if now.hour == 15 and now.minute >= 20:
            print(f"\n⚠️  MARKET CLOSING SOON - Options will be closed automatically")
        
        # EXIT CONDITIONS
        exit_signal = self.calculate_exit_conditions(current_pnl)
        if exit_signal and not self.kill_switch_activated and not self.dhan_kill_switch_active:
            print(f"\n⚠️  EXIT SIGNAL: {exit_signal}")
            
            if any(x in exit_signal for x in ["MAX LOSS", "TRAILING STOP", "MARKET CLOSE"]):
                print("\n🔄 AUTO EXIT INITIATED...")
                self.exit_all_option_positions()
                self.activate_dhan_kill_switch()
                self.kill_switch_activated = True
        
        # CURRENT POSITIONS
        print(f"\n📈 CURRENT OPTIONS POSITIONS ({len(option_positions)})")
        print("-"*120)
        if option_positions:
            for i, pos in enumerate(option_positions, 1):
                security_id = pos.get('securityId', 'Unknown')
                buy_qty = float(pos.get('buyQty', 0) or 0)
                sell_qty = float(pos.get('sellQty', 0) or 0)
                net_qty = abs(buy_qty - sell_qty)
                unrealized = float(pos.get('unrealizedProfit', 0) or 0)
                option_type = "CE" if 'CE' in security_id else "PE" if 'PE' in security_id else "OPT"
                print(f"   {i}. {security_id} | {option_type} | Qty: {net_qty:>5.0f} | P&L: ₹{unrealized:>8,.2f}")
        else:
            print("   No open Options positions")
        
        print("\n" + "="*120)
        print("⏳ Auto-refresh every 5 seconds | Press Ctrl+C to stop")
        print("="*120)
    
    def run(self):
        """Main loop"""
        try:
            while True:
                self.reset_if_new_day()
                self.display_dashboard()
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n\n👋 Dashboard stopped. Happy Trading!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(5)

# ============================================
# RUN DASHBOARD
# ============================================
if __name__ == "__main__":
    from config import CLIENT_ID, ACCESS_TOKEN, MAX_LOSS, TARGET, RISK
    
    dashboard = DhanTradingDashboard(
        client_id=CLIENT_ID,
        access_token=ACCESS_TOKEN,
        max_loss=MAX_LOSS,
        target=TARGET,
        risk=RISK
    )
    dashboard.run()