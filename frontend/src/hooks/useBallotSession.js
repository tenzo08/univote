import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'

export default function useBallotSession(options = {}) {
  return useQuery({
    queryKey: ['ballot-session'],
    queryFn: async () => {
      const { data } = await api.get('/voters/ballot-session/')
      return data
    },
    ...options,
  })
}
