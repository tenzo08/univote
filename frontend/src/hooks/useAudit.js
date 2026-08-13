import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'

export function useResults(electionId) {
  return useQuery({
    queryKey: ['results', electionId],
    queryFn: async () => {
      const { data } = await api.get(`/elections/${electionId}/results/`)
      return data
    },
    enabled: Boolean(electionId),
  })
}

export function useTurnout(electionId) {
  return useQuery({
    queryKey: ['turnout', electionId],
    queryFn: async () => {
      const { data } = await api.get(`/elections/${electionId}/turnout/`)
      return data
    },
    enabled: Boolean(electionId),
  })
}

export function useTimeline(electionId) {
  return useQuery({
    queryKey: ['timeline', electionId],
    queryFn: async () => {
      const { data } = await api.get(`/elections/${electionId}/timeline/`)
      return data
    },
    enabled: Boolean(electionId),
  })
}

export function useIntegrityReport(electionId) {
  return useQuery({
    queryKey: ['integrity-report', electionId],
    queryFn: async () => {
      const { data } = await api.get(`/elections/${electionId}/integrity-report/`)
      return data
    },
    enabled: Boolean(electionId),
  })
}
