import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'

export default function useCastBallot() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (selections) => {
      const { data } = await api.post('/voters/cast-ballot/', { selections })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ballot-session'] })
    },
  })
}
