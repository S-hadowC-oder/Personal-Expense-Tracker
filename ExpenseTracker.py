# Personal Expense Tracking Program
# Author: AI Assistant
# Version: 1.0
# Description: A comprehensive console-based expense tracker with database storage,
#              reporting, and budgeting features

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
import sys

class DatabaseManager:
    """Handles all database operations for the expense tracker."""
    
    def __init__(self, db_path: str = "expenses.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create the necessary tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create expenses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create budget table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS budget (
                    id INTEGER PRIMARY KEY,
                    monthly_budget REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create categories table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert default categories
            default_categories = ['Food', 'Travel', 'Rent', 'Shopping', 'Utilities', 'Healthcare', 'Entertainment']
            for category in default_categories:
                cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category,))
            
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
    
    def execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute a SELECT query and return results."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            return results
        except sqlite3.Error as e:
            print(f"Database query error: {e}")
            return []
    
    def execute_update(self, query: str, params: tuple = ()) -> bool:
        """Execute an INSERT, UPDATE, or DELETE query."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database update error: {e}")
            return False

class ExpenseManager:
    """Manages expense-related operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize with database manager."""
        self.db = db_manager
    
    def add_expense(self, date: str, category: str, amount: float, description: str) -> bool:
        """Add a new expense to the database."""
        query = "INSERT INTO expenses (date, category, amount, description) VALUES (?, ?, ?, ?)"
        return self.db.execute_update(query, (date, category, amount, description))
    
    def get_expenses(self, start_date: str = None, end_date: str = None, 
                    category: str = None, min_amount: float = None, 
                    max_amount: float = None, keyword: str = None) -> List[tuple]:
        """Retrieve expenses based on filters."""
        query = "SELECT id, date, category, amount, description FROM expenses WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if min_amount is not None:
            query += " AND amount >= ?"
            params.append(min_amount)
        
        if max_amount is not None:
            query += " AND amount <= ?"
            params.append(max_amount)
        
        if keyword:
            query += " AND description LIKE ?"
            params.append(f"%{keyword}%")
        
        query += " ORDER BY date DESC"
        
        return self.db.execute_query(query, tuple(params))
    
    def get_expense_summary(self, period: str = "monthly") -> Dict:
        """Get expense summary for different time periods."""
        today = datetime.now().date()
        
        if period == "daily":
            start_date = today.strftime('%Y-%m-%d')
            end_date = start_date
        elif period == "weekly":
            start_date = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif period == "monthly":
            start_date = today.replace(day=1).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif period == "yearly":
            start_date = today.replace(month=1, day=1).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        else:
            start_date = None
            end_date = None
        
        # Get total expenses
        if start_date and end_date:
            total_query = "SELECT SUM(amount) FROM expenses WHERE date BETWEEN ? AND ?"
            total_result = self.db.execute_query(total_query, (start_date, end_date))
        else:
            total_query = "SELECT SUM(amount) FROM expenses"
            total_result = self.db.execute_query(total_query)
        
        total_amount = total_result[0][0] if total_result[0][0] else 0.0
        
        # Get category-wise breakdown
        if start_date and end_date:
            category_query = """
                SELECT category, SUM(amount) as total 
                FROM expenses 
                WHERE date BETWEEN ? AND ? 
                GROUP BY category 
                ORDER BY total DESC
            """
            category_result = self.db.execute_query(category_query, (start_date, end_date))
        else:
            category_query = """
                SELECT category, SUM(amount) as total 
                FROM expenses 
                GROUP BY category 
                ORDER BY total DESC
            """
            category_result = self.db.execute_query(category_query)
        
        return {
            'total_amount': total_amount,
            'category_breakdown': category_result,
            'period': period,
            'start_date': start_date,
            'end_date': end_date
        }

class CategoryManager:
    """Manages expense categories."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize with database manager."""
        self.db = db_manager
    
    def get_categories(self) -> List[str]:
        """Get all available categories."""
        query = "SELECT name FROM categories ORDER BY name"
        results = self.db.execute_query(query)
        return [result[0] for result in results]
    
    def add_category(self, name: str) -> bool:
        """Add a new category."""
        query = "INSERT INTO categories (name) VALUES (?)"
        return self.db.execute_update(query, (name,))

class BudgetManager:
    """Manages budget-related operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize with database manager."""
        self.db = db_manager
    
    def set_monthly_budget(self, amount: float) -> bool:
        """Set or update monthly budget."""
        # Check if budget exists
        check_query = "SELECT id FROM budget WHERE id = 1"
        exists = self.db.execute_query(check_query)
        
        if exists:
            query = "UPDATE budget SET monthly_budget = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1"
        else:
            query = "INSERT INTO budget (id, monthly_budget) VALUES (1, ?)"
        
        return self.db.execute_update(query, (amount,))
    
    def get_monthly_budget(self) -> Optional[float]:
        """Get current monthly budget."""
        query = "SELECT monthly_budget FROM budget WHERE id = 1"
        result = self.db.execute_query(query)
        return result[0][0] if result else None
    
    def get_budget_status(self) -> Dict:
        """Get current budget status and spending."""
        budget = self.get_monthly_budget()
        if not budget:
            return {'budget': None, 'spent': 0, 'remaining': 0, 'percentage': 0}
        
        # Get current month spending
        today = datetime.now().date()
        month_start = today.replace(day=1).strftime('%Y-%m-%d')
        month_end = today.strftime('%Y-%m-%d')
        
        spent_query = "SELECT SUM(amount) FROM expenses WHERE date BETWEEN ? AND ?"
        spent_result = self.db.execute_query(spent_query, (month_start, month_end))
        spent = spent_result[0][0] if spent_result[0][0] else 0.0
        
        remaining = budget - spent
        percentage = (spent / budget) * 100 if budget > 0 else 0
        
        return {
            'budget': budget,
            'spent': spent,
            'remaining': remaining,
            'percentage': percentage
        }

class ReportGenerator:
    """Generates reports and visualizations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize with database manager."""
        self.db = db_manager
        self.ensure_reports_directory()
    
    def ensure_reports_directory(self):
        """Create reports directory if it doesn't exist."""
        if not os.path.exists('reports'):
            os.makedirs('reports')
    
    def generate_csv_report(self, filename: str = None) -> str:
        """Generate CSV report of all expenses."""
        if not filename:
            filename = f"expense_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join('reports', filename)
        
        query = "SELECT date, category, amount, description FROM expenses ORDER BY date DESC"
        expenses = self.db.execute_query(query)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Date', 'Category', 'Amount', 'Description'])
            writer.writerows(expenses)
        
        return filepath
    
    def generate_category_pie_chart(self, filename: str = None) -> str:
        """Generate pie chart for category-wise expenses."""
        if not filename:
            filename = f"category_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filepath = os.path.join('reports', filename)
        
        query = """
            SELECT category, SUM(amount) as total 
            FROM expenses 
            GROUP BY category 
            ORDER BY total DESC
        """
        results = self.db.execute_query(query)
        
        if not results:
            print("No data available for chart generation.")
            return None
        
        categories = [row[0] for row in results]
        amounts = [row[1] for row in results]
        
        plt.figure(figsize=(10, 8))
        plt.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
        plt.title('Expenses by Category')
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_monthly_bar_chart(self, filename: str = None) -> str:
        """Generate bar chart for monthly expenses."""
        if not filename:
            filename = f"monthly_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filepath = os.path.join('reports', filename)
        
        query = """
            SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
            FROM expenses 
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month
        """
        results = self.db.execute_query(query)
        
        if not results:
            print("No data available for chart generation.")
            return None
        
        months = [row[0] for row in results]
        amounts = [row[1] for row in results]
        
        plt.figure(figsize=(12, 6))
        plt.bar(months, amounts, color='skyblue', edgecolor='navy')
        plt.title('Monthly Expenses')
        plt.xlabel('Month')
        plt.ylabel('Amount ($)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filepath

class ExpenseTracker:
    """Main application class that coordinates all components."""
    
    def __init__(self):
        """Initialize all managers and components."""
        self.db_manager = DatabaseManager()
        self.expense_manager = ExpenseManager(self.db_manager)
        self.category_manager = CategoryManager(self.db_manager)
        self.budget_manager = BudgetManager(self.db_manager)
        self.report_generator = ReportGenerator(self.db_manager)
    
    def display_menu(self):
        """Display the main menu options."""
        print("\n" + "="*50)
        print("       PERSONAL EXPENSE TRACKER")
        print("="*50)
        print("1. Add Expense")
        print("2. View Summary")
        print("3. Search Expenses")
        print("4. Set/View Budget")
        print("5. Generate Report")
        print("6. Manage Categories")
        print("7. Exit")
        print("="*50)
    
    def get_user_input(self, prompt: str, input_type: type = str, default=None):
        """Get validated user input."""
        while True:
            try:
                user_input = input(prompt)
                if not user_input and default is not None:
                    return default
                if input_type == float:
                    return float(user_input)
                elif input_type == int:
                    return int(user_input)
                else:
                    return user_input
            except ValueError:
                print(f"Please enter a valid {input_type.__name__}.")
    
    def add_expense(self):
        """Add a new expense with user input."""
        print("\n--- Add New Expense ---")
        
        # Get date (default to today)
        today = datetime.now().strftime('%Y-%m-%d')
        date = self.get_user_input(f"Date (YYYY-MM-DD) [{today}]: ", default=today)
        
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
            return
        
        # Get category
        categories = self.category_manager.get_categories()
        print("\nAvailable categories:")
        for i, cat in enumerate(categories, 1):
            print(f"{i}. {cat}")
        print(f"{len(categories) + 1}. Add new category")
        
        choice = self.get_user_input("Select category number: ", int)
        
        if choice == len(categories) + 1:
            new_category = self.get_user_input("Enter new category name: ")
            if self.category_manager.add_category(new_category):
                category = new_category
                print(f"Category '{new_category}' added successfully!")
            else:
                print("Failed to add category.")
                return
        elif 1 <= choice <= len(categories):
            category = categories[choice - 1]
        else:
            print("Invalid selection.")
            return
        
        # Get amount
        amount = self.get_user_input("Amount ($): ", float)
        if amount <= 0:
            print("Amount must be positive.")
            return
        
        # Get description
        description = self.get_user_input("Description: ")
        
        # Add expense
        if self.expense_manager.add_expense(date, category, amount, description):
            print("✅ Expense added successfully!")
            
            # Check budget warning
            budget_status = self.budget_manager.get_budget_status()
            if budget_status['budget'] and budget_status['percentage'] > 80:
                print(f"⚠️  Budget Warning: You've spent {budget_status['percentage']:.1f}% of your monthly budget!")
        else:
            print("❌ Failed to add expense.")
    
    def view_summary(self):
        """Display expense summaries."""
        print("\n--- Expense Summary ---")
        print("1. Daily Summary")
        print("2. Weekly Summary")
        print("3. Monthly Summary")
        print("4. Yearly Summary")
        
        choice = self.get_user_input("Select summary type: ", int)
        
        periods = {1: "daily", 2: "weekly", 3: "monthly", 4: "yearly"}
        period = periods.get(choice)
        
        if not period:
            print("Invalid selection.")
            return
        
        summary = self.expense_manager.get_expense_summary(period)
        
        print(f"\n--- {period.title()} Summary ---")
        if summary['start_date'] and summary['end_date']:
            print(f"Period: {summary['start_date']} to {summary['end_date']}")
        print(f"Total Expenses: ${summary['total_amount']:.2f}")
        
        if summary['category_breakdown']:
            print("\nCategory Breakdown:")
            for category, amount in summary['category_breakdown']:
                percentage = (amount / summary['total_amount']) * 100 if summary['total_amount'] > 0 else 0
                print(f"  {category}: ${amount:.2f} ({percentage:.1f}%)")
            
            print(f"\nHighest spending category: {summary['category_breakdown'][0][0]}")
        else:
            print("No expenses found for this period.")
    
    def search_expenses(self):
        """Search and filter expenses."""
        print("\n--- Search Expenses ---")
        print("Leave fields empty to skip that filter:")
        
        start_date = self.get_user_input("Start date (YYYY-MM-DD): ", default=None)
        end_date = self.get_user_input("End date (YYYY-MM-DD): ", default=None)
        
        categories = self.category_manager.get_categories()
        print("\nAvailable categories:", ", ".join(categories))
        category = self.get_user_input("Category: ", default=None)
        
        min_amount_str = self.get_user_input("Minimum amount: ", default="")
        min_amount = float(min_amount_str) if min_amount_str else None
        
        max_amount_str = self.get_user_input("Maximum amount: ", default="")
        max_amount = float(max_amount_str) if max_amount_str else None
        
        keyword = self.get_user_input("Keyword in description: ", default=None)
        
        expenses = self.expense_manager.get_expenses(
            start_date=start_date,
            end_date=end_date,
            category=category,
            min_amount=min_amount,
            max_amount=max_amount,
            keyword=keyword
        )
        
        if expenses:
            print(f"\n--- Search Results ({len(expenses)} expenses found) ---")
            total = 0
            for expense in expenses:
                print(f"ID: {expense[0]} | Date: {expense[1]} | Category: {expense[2]} | "
                      f"Amount: ${expense[3]:.2f} | Description: {expense[4]}")
                total += expense[3]
            print(f"\nTotal Amount: ${total:.2f}")
        else:
            print("No expenses found matching your criteria.")
    
    def manage_budget(self):
        """Manage monthly budget."""
        print("\n--- Budget Management ---")
        print("1. Set Monthly Budget")
        print("2. View Budget Status")
        
        choice = self.get_user_input("Select option: ", int)
        
        if choice == 1:
            amount = self.get_user_input("Enter monthly budget amount: $", float)
            if amount > 0:
                if self.budget_manager.set_monthly_budget(amount):
                    print(f"✅ Monthly budget set to ${amount:.2f}")
                else:
                    print("❌ Failed to set budget.")
            else:
                print("Budget amount must be positive.")
        
        elif choice == 2:
            status = self.budget_manager.get_budget_status()
            if status['budget']:
                print(f"\n--- Budget Status ---")
                print(f"Monthly Budget: ${status['budget']:.2f}")
                print(f"Amount Spent: ${status['spent']:.2f}")
                print(f"Remaining: ${status['remaining']:.2f}")
                print(f"Percentage Used: {status['percentage']:.1f}%")
                
                if status['percentage'] > 100:
                    print("🚨 You've exceeded your budget!")
                elif status['percentage'] > 80:
                    print("⚠️  Warning: You're approaching your budget limit!")
                else:
                    print("✅ You're within budget.")
            else:
                print("No budget set. Please set a monthly budget first.")
        else:
            print("Invalid selection.")
    
    def generate_reports(self):
        """Generate various reports."""
        print("\n--- Generate Reports ---")
        print("1. Export to CSV")
        print("2. Generate Category Pie Chart")
        print("3. Generate Monthly Bar Chart")
        print("4. Generate All Reports")
        
        choice = self.get_user_input("Select report type: ", int)
        
        if choice == 1:
            filepath = self.report_generator.generate_csv_report()
            print(f"✅ CSV report generated: {filepath}")
        
        elif choice == 2:
            filepath = self.report_generator.generate_category_pie_chart()
            if filepath:
                print(f"✅ Pie chart generated: {filepath}")
        
        elif choice == 3:
            filepath = self.report_generator.generate_monthly_bar_chart()
            if filepath:
                print(f"✅ Bar chart generated: {filepath}")
        
        elif choice == 4:
            csv_file = self.report_generator.generate_csv_report()
            pie_chart = self.report_generator.generate_category_pie_chart()
            bar_chart = self.report_generator.generate_monthly_bar_chart()
            
            print("✅ All reports generated:")
            print(f"  - CSV: {csv_file}")
            if pie_chart:
                print(f"  - Pie Chart: {pie_chart}")
            if bar_chart:
                print(f"  - Bar Chart: {bar_chart}")
        
        else:
            print("Invalid selection.")
    
    def manage_categories(self):
        """Manage expense categories."""
        print("\n--- Manage Categories ---")
        categories = self.category_manager.get_categories()
        
        print("Current categories:")
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category}")
        
        print(f"\n{len(categories) + 1}. Add new category")
        choice = self.get_user_input("Select option: ", int)
        
        if choice == len(categories) + 1:
            new_category = self.get_user_input("Enter new category name: ")
            if self.category_manager.add_category(new_category):
                print(f"✅ Category '{new_category}' added successfully!")
            else:
                print("❌ Failed to add category. It might already exist.")
        else:
            print("Category management completed.")
    
    def run(self):
        """Main application loop."""
        print("Welcome to Personal Expense Tracker!")
        
        while True:
            try:
                self.display_menu()
                choice = self.get_user_input("Enter your choice (1-7): ", int)
                
                if choice == 1:
                    self.add_expense()
                elif choice == 2:
                    self.view_summary()
                elif choice == 3:
                    self.search_expenses()
                elif choice == 4:
                    self.manage_budget()
                elif choice == 5:
                    self.generate_reports()
                elif choice == 6:
                    self.manage_categories()
                elif choice == 7:
                    print("Thank you for using Personal Expense Tracker!")
                    break
                else:
                    print("Invalid choice. Please select 1-7.")
                
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\nExiting application...")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                input("Press Enter to continue...")

def main():
    """Entry point of the application."""
    try:
        # Check if required packages are installed
        required_packages = ['pandas', 'matplotlib']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print("Missing required packages:", ', '.join(missing_packages))
            print("Please install them using: pip install", ' '.join(missing_packages))
            return
        
        # Create and run the expense tracker
        tracker = ExpenseTracker()
        tracker.run()
        
    except Exception as e:
        print(f"Failed to start application: {e}")

if __name__ == "__main__":
    main()