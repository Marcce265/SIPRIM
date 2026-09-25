from backend.domain.entities.evaluacion_juridica import EvaluacionJuridica
from backend.domain.entities.proyecto import Proyecto
from backend.domain.ports.evaluacion_juridica_port import EvaluacionJuridicaPort
from backend.domain.value_objects.estado_evaluacion_juridica import (
    EstadoEvaluacionJuridica,
)


class EvaluacionJuridicaProvisionalAdapter(EvaluacionJuridicaPort):
    """Adaptador honesto mientras el servicio RAG juridico no esta disponible."""

    def evaluar(self, proyecto: Proyecto) -> EvaluacionJuridica:
        assert proyecto.id is not None
        return EvaluacionJuridica(
            proyecto_id=proyecto.id,
            estado=EstadoEvaluacionJuridica.PENDIENTE_VALIDACION_NORMATIVA,
            cumple=None,
            observaciones=(
                "La evaluacion juridica requiere integracion con el servicio RAG",
            ),
            fuentes=(),
        )
