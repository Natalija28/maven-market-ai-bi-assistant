print("====================================")
print(" Power BI AI Business Analyst")
print("====================================")

question = input("\nAsk a business question:\n> ")

print("\n------------------------------------")

if "profit" in question.lower():
    print("I would analyse:")
    print("- Total Profit")
    print("- Total Revenue")
    print("- Total Cost")
    print("- Profit Margin")
    print("- Revenue Target")

elif "revenue" in question.lower():
    print("I would analyse:")
    print("- Total Revenue")
    print("- YTD Revenue")
    print("- Last Month Revenue")
    print("- Revenue Target")

elif "transaction" in question.lower():
    print("I would analyse:")
    print("- Total Transactions")
    print("- Weekend Transactions")

else:
    print("Question recognised.")
    print("I would use the Power BI semantic model to answer it.")

print("\nRecommended visuals:")
print("- KPI Cards")
print("- Trend Chart")
print("- Product Analysis")
print("- Regional Analysis")
