import streamlit as st
import pandas as pd
import altair as alt
import re
import numpy as np

##################################

## Page Title
st.title("School Budget and Allocations")

###################################

## Utility functions
def moneyToFloat(money):
    value = float(re.sub(r'[^\d.]', '', money))
    return value

def removeLeadingZero(string):
    return(re.sub(r'^\d\d', '', string))

def year2FY(year):
    return(re.sub(r'-\d\d$', '', year))

###############################

## Read in Data

allocations = pd.read_csv("https://raw.githubusercontent.com/Erik-Brown01/School-Budget-and-Allocations/streamlit_visuals/data/district%205/allocation_district_5.csv")
allocations = allocations.drop(columns = ['Unnamed: 0'])
allocations['amountNum'] = allocations['amount'].apply((lambda x: moneyToFloat(x)))

budget = pd.read_csv("https://raw.githubusercontent.com/Erik-Brown01/School-Budget-and-Allocations/streamlit_visuals/data/district%205/budget_district_5.csv")
budget = budget.drop(columns = ['Unnamed: 0'])
budget['amountNum'] = budget['amount'].apply((lambda x: moneyToFloat(x)))

allocationCategories = pd.read_csv("https://raw.githubusercontent.com/Erik-Brown01/School-Budget-and-Allocations/streamlit_visuals/data/allocation_category_lookup.csv")

enrollment = pd.read_csv("https://raw.githubusercontent.com/Erik-Brown01/School-Budget-and-Allocations/streamlit_visuals/data/district%205/district_5_demographic_data.csv")
enrollment['DBN'] = enrollment['DBN'].apply(lambda x: removeLeadingZero(x))
enrollment['fiscal_year'] = enrollment['Year'].apply(lambda x: year2FY(x))
enrollment['Total Enrollment'] = enrollment['Total Enrollment'].str.replace(',', '').astype(float)


##############################

## Select Box

unique_school_codes = budget["location_code"].unique()
default_value = int(np.where(unique_school_codes == "M125")[0][0])
school_code = st.selectbox("Select School Code", unique_school_codes, index = default_value)
st.subheader(f"Data for School Code {school_code}")

################################

## Total Budget vs Allocations

st.subheader("Total Budget and Allocations")

# Calculate Total Budget Per Year for every location code
totalBudget = budget.groupby(by=['location_code', 'fiscal_year'])['amountNum'].sum().reset_index()
totalBudget = totalBudget.rename(columns = {'amountNum': 'total'})
totalBudget['type'] = 'budget'

# Calculate Total Allocations Per Year for every location code
totalAllocations = allocations.groupby(by=['location_code', 'fiscal_year'])['amountNum'].sum().reset_index()
totalAllocations = totalAllocations.rename(columns = {'amountNum': 'total'})
totalAllocations['type'] = 'allocations'

# Combine Total Allocations and Budget into one df
totals = pd.concat([totalBudget, totalAllocations])

# Create Totals Pivot Table
totalsPivot = totals.pivot(index = ['location_code', 'type'], columns = ['fiscal_year'], values = ['total']).reset_index()
totalsPivot.columns = totalsPivot.columns.to_flat_index()
totalsPivot = totalsPivot.reset_index()
new_columns = ['index', 'location_code', 'type', '2018', '2019', '2020', '2021', '2022']
totalsPivot.columns = new_columns
totalsPivot =  totalsPivot.drop(columns = 'index')

# Format totals so that it can be read by altair
totalsMelt = totalsPivot.melt(id_vars=["location_code", "type"], var_name="year", value_name="amount")
totalsMelt["amount"] = totalsMelt["amount"].astype(float)

# Filter for school_code
filtered_totalsMelt = totalsMelt[totalsMelt["location_code"] == school_code]

# Create line chart
line = (
    alt.Chart(filtered_totalsMelt)
    .mark_line()
    .encode(
        x=alt.X("year:O"),
        y=alt.Y("amount:Q"),
        color="type:N",
    )
)

# Create dots for line chart
dots = (
    alt.Chart(filtered_totalsMelt)
    .mark_circle(size=100)
    .encode(
        x=alt.X("year:O"),
        y=alt.Y("amount:Q"),
        color="type:N",
        tooltip=["type", "year", "amount"],
    )
)

# Display Line chart
budgets_allocations_chart = (line + dots).properties(width=600, height=400, title="Budget vs Allocations")
st.altair_chart(budgets_allocations_chart, use_container_width=True)

#######################################

## Funding per Allocation Category

st.subheader("Funding per Category")

# Assign category to every allocation 
# Allocation categories were provided by Anna Minksy (Manhattan CEC 5)
district_5_allocation_categories = allocations.merge(allocationCategories, how = 'left', left_on = 'allocation_category', right_on = 'allocation_category')

# Calculate total funding, per category per school, per year
funding_per_category = district_5_allocation_categories.groupby(by = ['location_code', 'fiscal_year', 'allocation_category_group'])['amountNum'].sum().reset_index()

# Make a funding per category table (used later)
funding_per_category_pivot = funding_per_category.pivot(index = ['location_code', 'allocation_category_group'], columns = ['fiscal_year'], values = 'amountNum').reset_index()

#Filter table to selected school code
funding_per_category_filtered = funding_per_category[funding_per_category['location_code'] == school_code]

# Create funding per category per year chart
funding_per_category_chart = (
    alt.Chart(funding_per_category_filtered)
    .mark_bar()
    .encode(
        x=alt.X("fiscal_year:O", title="Fiscal Year"),
        y=alt.Y("amountNum:Q", title="Funding Amount"),
        color=alt.Color("allocation_category_group:N", title="Allocation Category"),
        tooltip=["allocation_category_group", "fiscal_year", "amountNum"],
    )
    .properties(width=600, height=400, title="Funding per Allocation Category")
)

#Display chart
st.altair_chart(funding_per_category_chart, use_container_width=True)

######################################

## Enrollment and Funding 

st.subheader("Enrollment and Funding")

# Make enrollment calculated columns
enrollment['3K-PreK_enrollment'] = enrollment['Grade 3K'] + enrollment['Grade PK (Half Day & Full Day)']
enrollment['K-5_enrollment'] = enrollment['Total Enrollment'] - enrollment['3K-PreK_enrollment']

# Make Pre-K Enrollment Pivot
preK_pivot = enrollment[['DBN','fiscal_year','3K-PreK_enrollment']].pivot(index = ['DBN'], columns = ['fiscal_year'], values = '3K-PreK_enrollment').reset_index()
preK_pivot['Grades'] = '3K-PreK Enrollment'

# Make K-5 Enrollment Pivot
elementary_pivot = enrollment[['DBN','fiscal_year','K-5_enrollment']].pivot(index = ['DBN'], columns = ['fiscal_year'], values = 'K-5_enrollment').reset_index()
elementary_pivot['Grades'] = 'K-5 Enrollment'

# Concat Pre-K Enrollment Pivot and K-5 Enrollment Pivot
enrollmentPivot = pd.concat([preK_pivot, elementary_pivot])
enrollmentPivot = enrollmentPivot.rename(columns = {'Grades':'Type'})

# Get Fair Student Funding and Pre-school funding from funding_per_category_pivot
relevant_funding_per_category_pivot = funding_per_category_pivot[funding_per_category_pivot['allocation_category_group'].isin(['Fair Student Funding', 'Preschool'])]
relevant_funding_per_category_pivot = relevant_funding_per_category_pivot.rename(columns = {'allocation_category_group': 'Type', 'location_code': 'DBN', 2018:'2018', 2019:'2019', 2020:'2020', 2021:'2021'})
relevant_funding_per_category_pivot = relevant_funding_per_category_pivot.drop(columns = [2022])

# Currently scraped funding data only goes back to 2018
enrollmentPivot = enrollmentPivot.drop(columns = '2017')

# Concat FSF and Pre-K Funding Pivot to Enrollment Pivot
enrollment_and_funding_pivot = pd.concat([enrollmentPivot, relevant_funding_per_category_pivot])

# Melt the DataFrame to have years as rows
enrollment_and_funding_melted = enrollment_and_funding_pivot.melt(
    id_vars=["DBN", "Type"],
    var_name="year",
    value_name="value",
)

# Cast year column to int
enrollment_and_funding_melted["year"] = enrollment_and_funding_melted["year"].astype(int)

# This function modifies the value column 
def update_type_and_value(row):
    if row["Type"] == "Preschool":
        return "Preschool Funding / 10,000", row["value"] / 10000
    elif row["Type"] == "Fair Student Funding":
        return "Fair Student Funding / 10,000", row["value"] / 10000
    else:
        return row["Type"], row["value"]

enrollment_and_funding_melted[["Type", "value"]] = enrollment_and_funding_melted.apply(update_type_and_value, axis=1, result_type="expand")

# Filter to selected school code
filtered_enrollment_and_funding_melted = enrollment_and_funding_melted[enrollment_and_funding_melted["DBN"] == school_code]


# Create a list of line types
line_types = ["3K-PreK Enrollment", "K-5 Enrollment", "Fair Student Funding / 10,000", "Preschool Funding / 10,000"]

# Create the base chart
base = alt.Chart(filtered_enrollment_and_funding_melted).encode(
    x=alt.X("year:O", scale=alt.Scale(zero=False), axis=alt.Axis(format="d")),
    y="value:Q",
    color="Type:N",
    tooltip=["DBN", "Type", "year", "value"],
)

# Create the multi-line chart
multiline_chart = alt.layer(
    *[base.transform_filter(alt.datum["Type"] == line_type).mark_line() for line_type in line_types]
).properties(width=600, height=400, title="Enrollment and Funding by Type")

# Display multi-line chart in Streamlit
st.altair_chart(multiline_chart, use_container_width=True)

#########################################

## Staff and Enrollment

st.subheader("Staff and Enrollment")

# Get only teaching budget rows
teaching_budget = budget[budget['budget_category'].isin(['Paraprofessionals', 'Classroom Teacher', 'Homeroom Teacher', 'Elementary Cluster/Quota', 'Cluster/Quota Teacher'])]

# Thse are all counted toward the total for teaching staff
teaching_budget['budget_category'] = teaching_budget['budget_category'].replace(['Classroom Teacher', 'Homeroom Teacher', 'Elementary Cluster/Quota', 'Cluster/Quota Teacher'], 'Teacher')

# Calculate total teacher and paraprofessional positions
positions_per_school = teaching_budget.groupby(by = ['location_code', 'fiscal_year', 'budget_category'])['num_positions'].sum().reset_index()

# Make positions per school pivot
positions_per_school_pivot = positions_per_school.pivot(index = ['location_code', 'budget_category'], columns = 'fiscal_year', values = 'num_positions').reset_index()
positions_per_school_pivot = positions_per_school_pivot.rename(columns = {'budget_category': 'type'})
positions_per_school_pivot = positions_per_school_pivot.rename(columns = {2018:'2018', 2019:'2019', 2020:'2020', 2021:'2021'})

# Get Total Enrollment per year
total_enrollment = enrollment[['DBN','fiscal_year', 'Total Enrollment']]
total_enrollment = total_enrollment.rename(columns = {'DBN': 'location_code'})

# Make Total Enrollment Pivot
total_enrollment_pivot = total_enrollment.pivot(index = 'location_code', columns = 'fiscal_year', values = 'Total Enrollment').reset_index()
total_enrollment_pivot['type'] = 'Total Enrollment'

# Concat totalEnrollmentPivot and positions_per_school_pivot
staff_and_enrollment = pd.concat([total_enrollment_pivot,positions_per_school_pivot])
staff_and_enrollment = staff_and_enrollment.drop(columns = ['2017', 2022])

# Melt the data so it can be read by altair
staff_and_enrollment_melt = staff_and_enrollment.melt(id_vars=["location_code", "type"], var_name="year", value_name="amount")

# Modify Total Enrollment values
staff_and_enrollment_melt.loc[staff_and_enrollment_melt["type"] == "Total Enrollment", "amount"] /= 10

# Filter for school_code
filtered_staff_and_enrollment_melt = staff_and_enrollment_melt[staff_and_enrollment_melt["location_code"] == school_code]

# Create line chart
staff_and_enrollment_chart = (
    alt.Chart(filtered_staff_and_enrollment_melt)
    .mark_line()
    .encode(
        x="year:O",
        y="amount:Q",
        color="type:N",
        tooltip=["type", "amount"],
    )
    .properties(width=600, height=400, title="Total Enrollment / 10, Teacher, and Paraprofessionals")
)

# Display chart
st.altair_chart(staff_and_enrollment_chart, use_container_width=True)

##############################################

## Budget and Staff

st.subheader("Budget and Staff")

# Calculate average budget per para and teacher 
pos_and_budget = teaching_budget.groupby(by = ['location_code', 'fiscal_year', 'budget_category'])['amountNum'].sum().reset_index()
budget_per_staff = pos_and_budget.merge(positions_per_school, on = ['location_code','fiscal_year','budget_category'])
budget_per_staff['average_budget'] = budget_per_staff['amountNum'].astype(float)/budget_per_staff['num_positions']

# Filter to only selected school code 
budget_per_staff_filtered = budget_per_staff[budget_per_staff["location_code"] == school_code]

# Create and display bar chart for each FY
for fiscal_year in budget_per_staff_filtered['fiscal_year'].unique():
    budget_per_staff_filtered_temp = budget_per_staff_filtered[budget_per_staff_filtered['fiscal_year'] == fiscal_year]
    budget_per_staff_chart = (
        alt.Chart(budget_per_staff_filtered_temp)
        .mark_bar()
        .encode(
            x=alt.X("budget_category:N", title="Budget Category"),
            y=alt.Y("average_budget:Q", title="Average Budget"),
            color=alt.Color("budget_category:N", title="Staff Type"),
            #column=alt.Column("fiscal_year:O", title="Fiscal Year"),
            tooltip=["budget_category", "fiscal_year", "average_budget"],
        )
        .properties(width=600, height=400, title="Average Budget for Teachers and Paraprofessionals FY" + str(fiscal_year))
    )

    # Display chart
    st.altair_chart(budget_per_staff_chart, use_container_width=True)