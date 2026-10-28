"""Local, synthetic-only Streamlit fixture for the browser contract check."""
import streamlit as st
from chart_cases import chart_case

st.set_page_config(layout='wide')
case = st.radio('Chart case', ['weekly', 'daily', 'compact', 'review'], horizontal=True)
st.plotly_chart(chart_case(case), key=f'chart_{case}', config={'scrollZoom': True})
