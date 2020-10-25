import frappe
from frappe import _
from frappe import utils

"""
Todo


Complete functionality
b. Add settings fields to Accounts Settings
    Section: Expense Settings
    - Link: Default Payment Account (Link: Mode of Payment) 
      - Desc: Create a Mode of Payment for expenses and link it to your usual expenditure account like Petty Cash
    - Checkbox: Notify all Approvers
      - Desc: when a expense request is made
    - Checkbox: Create Journals Automatically

Add all the fixtures to the app so that it is fully portable
a. Workflows
b. Accounts Settings Fields
c. Fix minor issues
   - Cant set custom print format as default - without customisation

Report




Rename App

Tests

More Features - v2
- Alert Approvers - manual - for pending / draft
- Tax Templates
- Separate Request Document
   - Add approved amount on expense entry - auto filled from requested amount but changeable

- Fix
    - Prevent Making JE's before submission / non-approvers

- Add dependant fields
    - Workflow entries
    - JV type: Expense Entry
    - JV Account Reference Type: Expense Entry
    - Mode of Payment: Petty Cash


Done
  - Issues Fixed
    - Wire Transfer requires reference date, and minor improvements
    - Approver field vanishing
  
  - Print Format improvements - (Not done: Add signatures)
  - Prevent duplicate entry - done
  - Workflow: Pending Approval, Approved (set-approved by)
  - Creation of JV
  - expense refs
  - Roles:
    - Expense Approver
  - Set authorising party

  Add sections to EE and EE Items
    Section: Accounting Dimensions
    - Project
    - Cost Center

Enhancements
- Added Cost Center Filters
"""


def setup(expense_entry, method):

    # add expenses and set the total field

    total = 0
    count = 0
    for detail in expense_entry.expenses:
        total += float(detail.amount)        
        count += 1

    expense_entry.total = total
    expense_entry.quantity = count

    make_journal_entry(expense_entry)

    


@frappe.whitelist()
def initialise_journal_entry(expense_entry_name):
    # make JE from javascript form Make JE button

    make_journal_entry(
        frappe.get_doc('Expense Entry', expense_entry_name)
    )


def make_journal_entry(expense_entry):

    if expense_entry.status == "Approved":         

        # check for duplicates
        
        if frappe.db.exists({'doctype': 'Journal Entry', 'bill_no': expense_entry.name}):
            frappe.throw(
                title="Error",
                msg="Journal Entry {} already exists.".format(expense_entry.name)
            )


        # Preparing the JE: convert expense_entry details into je account details

        accounts = []

        for detail in expense_entry.expenses:
            expense_project = ""
            expense_cost_center = ""
            
            if not detail.project and expense_entry.default_project:
                expense_project = expense_entry.default_project
            else:
                expense_project = detail.project
            
            if not detail.cost_center and expense_entry.default_cost_center:
                expense_cost_center = expense_entry.default_cost_center
            else:
                expense_cost_center = detail.cost_center

            

            accounts.append({  
                'debit_in_account_currency': float(detail.amount),
                'user_remark': str(detail.description),
                'account': detail.expense_account,
                'project': expense_project,
                'cost_center': expense_cost_center
            })

        # finally add the payment account detail

        pay_account = ""

        if (expense_entry.mode_of_payment != "Cash" and expense_entry.mode_of_payment != "Wire Transfer") and (not expense_entry.payment_reference):
            frappe.throw(
                title="Enter Payment Reference",
                msg="Payment Reference is Required for all non-cash payments."
            )

        payment_mode = frappe.get_doc('Mode of Payment', expense_entry.mode_of_payment)
        for acc in payment_mode.accounts:
            pay_account = acc.default_account

        if not pay_account or pay_account == "":
            frappe.throw(
                title="Error",
                msg="The selected Mode of Payment has no linked account."
            )

        accounts.append({  
            'credit_in_account_currency': float(expense_entry.total),
            'user_remark': str(detail.description),
            'account': pay_account
        })

        # create the journal entry
        je = frappe.get_doc({
            'title': expense_entry.name,
            'doctype': 'Journal Entry',
            'voucher_type': 'Journal Entry',
            'posting_date': utils.today(),
            'company': expense_entry.company,
            'accounts': accounts,
            'user_remark': expense_entry.remarks,
            'mode_of_payment': expense_entry.mode_of_payment,
            'cheque_date': expense_entry.clearance_date,
            'reference_date': expense_entry.clearance_date,
            'cheque_no': expense_entry.payment_reference,
            'pay_to_recd_from': expense_entry.payment_to,
            'bill_no': expense_entry.name
        })

        user = frappe.get_doc("User", frappe.session.user)

        full_name = str(user.first_name) + ' ' + str(user.last_name)
        expense_entry.db_set('approved_by', full_name)
        

        je.insert()
        je.submit()