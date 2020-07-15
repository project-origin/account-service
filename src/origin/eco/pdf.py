import plotly.graph_objects as go
from io import BytesIO
from jinja2 import Template
from functools import partial
from weasyprint import HTML, default_url_fetcher

from origin.settings import (
    ECO_DECLARATION_PDF_TEMPLATE_PATH,
    UNKNOWN_TECHNOLOGY_LABEL,
)

from .declaration import EcoDeclaration


TECHNOLOGY_COLORS_DEFAULT = 'black'

TECHNOLOGY_COLORS = {
    'Wind': '#0a515d',
    'Marine': '#f29e1f',
    'Hydro': '#00a98f',
    'Solar': '#ffd424',
    'Biomass': '#a0cd92',
    'Biogas': '#293a4c',
    'Waste': '#a0c1c2',
    'Coal': '#333333',
    'Naturalgas': '#a0ffc8',
    'Oil': '#ff6600',
    'Nuclear': '#8064a2',
    UNKNOWN_TECHNOLOGY_LABEL: '#4bacc6',
}


def build_pie_chart(declaration):
    """
    :param EcoDeclaration declaration:
    """
    try:
        f = BytesIO()

        labels = []
        values = []
        colors = []

        for technology, amount in declaration.technologies.items():
            labels.append(technology)
            values.append(amount)
            colors.append(TECHNOLOGY_COLORS.get(
                technology, TECHNOLOGY_COLORS_DEFAULT))

        x = 2
        y = 3

        pie = go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors),
        )

        fig = go.Figure(data=[pie])
        fig.update_traces(textinfo='none')
        fig.update_layout(
            showlegend=False,
            autosize=False,
            width=500,
            height=500,
            margin=dict(l=0, r=0, b=0, t=0, pad=0),
        )
        fig.write_image(f, format='svg')

        f.seek(0)
    except Exception as e:
        x = 2
        raise

    return f


def url_fetcher(individual, general, url, *args, **kwargs):
    if url.endswith('/individual-declaration.svg'):
        return {'file_obj': build_pie_chart(individual)}
    elif url.endswith('/general-declaration.svg'):
        return {'file_obj': build_pie_chart(general)}
    else:
        return default_url_fetcher(url, *args, **kwargs)


class EcoDeclarationPdf(object):
    def technologies_to_env(self, declaration):
        """
        :param EcoDeclaration declaration:
        :rtype: list[dict[str, str]]
        """
        technologies_sorted = sorted(declaration.technologies.keys())
        technologies_percentage = declaration.technologies_percentage

        return [
            {
                'technology': technology,
                'amount': declaration.technologies[technology],
                'percent': technologies_percentage[technology],
                'color': TECHNOLOGY_COLORS.get(
                    technology, TECHNOLOGY_COLORS_DEFAULT),
            }
            for technology in technologies_sorted
        ]

    def get_html_template(self):
        """
        :rtype: Template
        """
        with open(ECO_DECLARATION_PDF_TEMPLATE_PATH) as f:
            return Template(f.read())

    def render_html(self, individual, general):
        """
        :param EcoDeclaration individual:
        :param EcoDeclaration general:
        :rtype: str
        """
        env = dict(
            individual_emissions=individual.total_emissions_per_wh * 1000,
            individual_technologies=self.technologies_to_env(individual),
            general_emissions=general.total_emissions_per_wh * 1000,
            general_technologies=self.technologies_to_env(general),
        )
        return self.get_html_template().render(
            individual_emissions=individual.total_emissions_per_wh * 1000,
            individual_technologies=self.technologies_to_env(individual),
            general_emissions=general.total_emissions_per_wh * 1000,
            general_technologies=self.technologies_to_env(general),
        )

    def render(self, individual, general, target):
        """
        :param EcoDeclaration individual:
        :param EcoDeclaration general:
        :param file target:
        """

        # Render HTML
        html = self.render_html(individual, general)

        # Render PDF from HTML + write to target
        HTML(
            string=html,
            url_fetcher=partial(url_fetcher, individual, general),
        ).write_pdf(target)
