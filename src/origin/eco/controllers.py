import marshmallow_dataclass as md

from origin.db import inject_session
from origin.http import Controller, BadRequest
from origin.auth import (
    User,
    MeteringPointQuery,
    inject_user,
    require_oauth,
)

from .builder import EcoDeclarationBuilder
from .models import GetEcoDeclarationRequest, GetEcoDeclarationResponse


builder = EcoDeclarationBuilder()


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
        :rtype: GetGgoListResponse
        """
        meteringpoints = MeteringPointQuery(session) \
            .belongs_to(user) \
            .has_any_gsrn(request.gsrn) \
            .all()

        gsrn = [m.gsrn for m in meteringpoints]

        if len(gsrn) < len(request.gsrn):
            raise BadRequest((
                'Could not load the following MeteringPoints: %s'
            ) % ', '.join([g for g in request.gsrn if g not in gsrn]))

        individual, general = builder.build_eco_declaration(
            user=user,
            meteringpoints=meteringpoints,
            begin_from=request.begin_range.begin,
            begin_to=request.begin_range.end,
            session=session,
        )

        return GetEcoDeclarationResponse(
            success=True,
            individual=individual.as_resolution(request.resolution),
            general=general.as_resolution(request.resolution),
        )
