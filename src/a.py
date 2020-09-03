# import plotly.graph_objects as go
# from weasyprint import HTML, default_url_fetcher
# from io import BytesIO
#
#
# def build_individual_pie_chart():
#     f = BytesIO()
#
#     labels = ['Oxygen','Hydrogen','Carbon_Dioxide','Nitrogen']
#     values = [4500, 2500, 1053, 500]
#
#     fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
#     fig.update_layout(
#         showlegend=False,
#         autosize=False,
#         width=250,
#         height=250,
#         margin=dict(l=0, r=0, b=0, t=0, pad=0),
#         # paper_bgcolor="LightSteelBlue",
#     )
#     fig.write_image(f, format='svg')
#
#     f.seek(0)
#
#     return f
#
#
# def url_fetcher(url, *args, **kwargs):
#     if url.endswith('/individual-declaration.svg'):
#         return {'file_obj': build_individual_pie_chart()}
#     elif url.endswith('/general-declaration.svg'):
#         return {'file_obj': build_individual_pie_chart()}
#     else:
#         return default_url_fetcher(url, *args, **kwargs)
#
#
# html = HTML('template.html', url_fetcher=url_fetcher)
# html.write_pdf('asd.pdf')

from datetime import datetime, timezone, timedelta
from io import BytesIO

from origin.db import make_session
from origin.common import DateTimeRange
from origin.auth import UserQuery, MeteringPointQuery
from origin.eco import EcoDeclarationBuilder, EcoDeclarationPdf


# f = BytesIO()

session = make_session()
user = UserQuery(session).one()
meteringpoints = MeteringPointQuery(session).is_consumption().all()
begin_range = DateTimeRange(
    begin=datetime(2019, 9, 18, 0, 0, tzinfo=timezone(timedelta(hours=2))),
    end=datetime(2019, 9, 18, 23, 59, tzinfo=timezone(timedelta(hours=2))),
)

individual, general = EcoDeclarationBuilder().build_eco_declaration(
    user=user,
    meteringpoints=meteringpoints,
    begin_range=begin_range,
    session=session,
)

pdf = EcoDeclarationPdf()
pdf.render(individual, general, open('asd2.pdf', 'wb'))
