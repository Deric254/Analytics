import plotly.express as px

def bar_chart(df, x, y, title="Bar Chart"):
    return px.bar(df, x=x, y=y, title=title)

def line_chart(df, x, y, title="Line Chart"):
    return px.line(df, x=x, y=y, title=title)

def scatter_chart(df, x, y, title="Scatter Chart"):
    return px.scatter(df, x=x, y=y, title=title)

def pie_chart(df, names, values, title="Pie Chart"):
    return px.pie(df, names=names, values=values, title=title)

def heatmap(df, title="Heatmap"):
    return px.imshow(df.corr(), text_auto=True, title=title)
