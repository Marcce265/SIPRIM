import type { CriteriaVersion, EconomicResult, ProjectVersion } from '../types/proyecto'

const roundTwo = (value: number) => Math.round((value + Number.EPSILON) * 100) / 100

export function validateEconomicCriteria(
  excellentCost: number,
  unacceptableCost: number,
): string[] {
  const errors: string[] = []
  if (!Number.isFinite(excellentCost) || excellentCost <= 0) {
    errors.push('El umbral excelente debe ser mayor que cero.')
  }
  if (!Number.isFinite(unacceptableCost) || unacceptableCost <= 0) {
    errors.push('El umbral inaceptable debe ser mayor que cero.')
  }
  if (
    Number.isFinite(excellentCost) &&
    Number.isFinite(unacceptableCost) &&
    excellentCost >= unacceptableCost
  ) {
    errors.push('El umbral excelente debe ser menor que el inaceptable.')
  }
  return errors
}

export function evaluateEconomicProject(
  project: Pick<ProjectVersion, 'presupuesto' | 'beneficiarios'>,
  criteria: Pick<CriteriaVersion, 'costoExcelente' | 'costoInaceptable' | 'pesoEconomico'>,
  calculatedAt = new Date().toISOString(),
): EconomicResult {
  if (!Number.isFinite(project.presupuesto) || project.presupuesto <= 0) {
    throw new Error('El presupuesto debe ser mayor que cero.')
  }
  if (!Number.isInteger(project.beneficiarios) || project.beneficiarios <= 0) {
    throw new Error('Los beneficiarios deben ser un entero mayor que cero.')
  }
  const criteriaErrors = validateEconomicCriteria(
    criteria.costoExcelente,
    criteria.costoInaceptable,
  )
  if (criteriaErrors.length > 0) throw new Error(criteriaErrors.join(' '))

  const exactCost = project.presupuesto / project.beneficiarios
  let score: number
  if (exactCost <= criteria.costoExcelente) {
    score = 100
  } else if (exactCost >= criteria.costoInaceptable) {
    score = 0
  } else {
    score =
      (100 * (criteria.costoInaceptable - exactCost)) /
      (criteria.costoInaceptable - criteria.costoExcelente)
  }

  const cost = roundTwo(exactCost)
  const roundedScore = roundTwo(Math.min(100, Math.max(0, score)))
  return {
    presupuesto: project.presupuesto,
    beneficiarios: project.beneficiarios,
    costoPorBeneficiario: cost,
    formula: 'presupuesto / beneficiarios',
    costoExcelente: criteria.costoExcelente,
    costoInaceptable: criteria.costoInaceptable,
    pesoEconomico: criteria.pesoEconomico,
    puntuacion: roundedScore,
    explicacion:
      `Costo por beneficiario: S/ ${project.presupuesto.toFixed(2)} / ` +
      `${project.beneficiarios} = S/ ${cost.toFixed(2)}. ` +
      `La puntuación ${roundedScore.toFixed(2)}/100 se obtiene con el criterio ` +
      'académico de comparación y no constituye una declaración de viabilidad.',
    versionAlgoritmo: 'criterio-economico-academico-v1',
    fechaCalculo: calculatedAt,
  }
}
