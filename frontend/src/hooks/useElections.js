import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'

export function useElections() {
  return useQuery({
    queryKey: ['elections'],
    queryFn: async () => {
      const { data } = await api.get('/elections/')
      return data.results ?? data
    },
  })
}

export function useElection(electionId) {
  return useQuery({
    queryKey: ['elections', electionId],
    queryFn: async () => {
      const { data } = await api.get(`/elections/${electionId}/`)
      return data
    },
    enabled: Boolean(electionId),
  })
}

export function useCreateElection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload) => {
      const { data } = await api.post('/elections/', payload)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['elections'] }),
  })
}

export function usePublishElection(electionId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/elections/${electionId}/publish/`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['elections'] })
    },
  })
}

export function useArchiveElection(electionId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/elections/${electionId}/archive/`)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['elections'] }),
  })
}

export function useAddPosition(electionId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload) => {
      const { data } = await api.post(`/elections/${electionId}/positions/`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['elections', electionId] })
      queryClient.invalidateQueries({ queryKey: ['elections'] })
    },
  })
}
