import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'

export function useRoster(electionId, { q = '', limit = 20, offset = 0 } = {}) {
  return useQuery({
    queryKey: ['roster', electionId, q, limit, offset],
    queryFn: async () => {
      const { data } = await api.get(`/admin/election-voter-roster/${electionId}/`, {
        params: { q, limit, offset },
      })
      return data
    },
    enabled: Boolean(electionId),
    placeholderData: (previous) => previous,
  })
}

export function useUploadRosterCsv(electionId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (file) => {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post('/voters/upload-csv/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roster', electionId] }),
  })
}

export function useEnrollVoters(electionId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (voterIds) => {
      const { data } = await api.post(`/admin/election-voter-roster/${electionId}/enroll/`, { voter_ids: voterIds })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roster', electionId] }),
  })
}

export function useUnenrollVoters(electionId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (voterIds) => {
      const { data } = await api.post(`/admin/election-voter-roster/${electionId}/unenroll/`, { voter_ids: voterIds })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roster', electionId] }),
  })
}

export function useClearRoster(electionId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/admin/election-voter-roster/${electionId}/clear/`)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roster', electionId] }),
  })
}
