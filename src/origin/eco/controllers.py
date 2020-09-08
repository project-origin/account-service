from io import BytesIO
from flask import make_response, send_file
import marshmallow_dataclass as md

from origin.db import inject_session
from origin.http import Controller, BadRequest
from origin.auth import (
    User,
    MeteringPointQuery,
    inject_user,
    require_oauth,
)

from .pdf import EcoDeclarationPdf
from .builder import EcoDeclarationBuilder
from .models import GetEcoDeclarationRequest, GetEcoDeclarationResponse


builder = EcoDeclarationBuilder()
pdf_builder = EcoDeclarationPdf()


class GetEcoDeclaration(Controller):
    """
    TODO
    """
    Request = md.class_schema(GetEcoDeclarationRequest)
    Response = md.class_schema(GetEcoDeclarationResponse)

    @require_oauth('ggo.read')
    @inject_user
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetEcoDeclarationRequest request:
        :param User user:
        :param sqlalchemy.orm.Session session:
        :rtype: GetEcoDeclarationResponse
        """
        meteringpoints = MeteringPointQuery(session) \
            .belongs_to(user) \
            .has_any_gsrn(request.gsrn) \
            .is_consumption() \
            .all()

        gsrn = [m.gsrn for m in meteringpoints]

        if len(gsrn) < len(request.gsrn):
            raise BadRequest((
                'Could not load the following MeteringPoints: %s'
            ) % ', '.join([g for g in request.gsrn if g not in gsrn]))

        individual, general = builder.build_eco_declaration(
            user=user,
            meteringpoints=meteringpoints,
            begin_range=request.begin_range,
            session=session,
        )

        return GetEcoDeclarationResponse(
            success=True,
            individual=individual.as_resolution(
                request.resolution, request.utc_offset),
            general=general.as_resolution(
                request.resolution, request.utc_offset),
        )


class ExportEcoDeclarationPDF(GetEcoDeclaration):
    """
    TODO
    """
    Response = None

    def handle_request(self, *args, **kwargs):
        response_model = super(ExportEcoDeclarationPDF, self) \
            .handle_request(*args, **kwargs)

        f = BytesIO()

        pdf_builder.render(
            individual=response_model.individual,
            general=response_model.general,
            target=f,
        )

        f.seek(0)

        return send_file(f, attachment_filename='EnvironmentDeclaration.pdf')

        # response = make_response(f.read())
        # response.headers['Content-Type'] = 'application/pdf'
        # response.headers['Content-Disposition'] = \
        #     'inline; filename=EnvironmentDeclaration.pdf'
        #
        # return response
