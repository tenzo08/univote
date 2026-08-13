import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'

export function useCandidates(electionId) {
  return useQuery({
    queryKey: ['candidates', electionId],
    queryFn: async () => {
      const { data } = await api.get(`/elections/${electionId}/candidates/`)
      return data
    },
    enabled: Boolean(electionId),
  })
}

export function useRegisterCandidate(electionId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload) => {
      const { data } = await api.post(`/elections/${electionId}/candidates/`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates', electionId] })
      queryClient.invalidateQueries({ queryKey: ['elections', electionId] })
    },
  })
}

export function useUpdateCandidate(electionId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ candidateId, payload }) => {
      const { data } = await api.patch(`/elections/${electionId}/candidates/${candidateId}/`, payload)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['candidates', electionId] }),
  })
}

export function useDeleteCandidate(electionId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (candidateId) => {
      await api.delete(`/elections/${electionId}/candidates/${candidateId}/`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates', electionId] })
      queryClient.invalidateQueries({ queryKey: ['elections', electionId] })
    },
  })
}
