import { ref } from 'vue'
import { TicketAPI } from '@/api/module_system/ticket'

/**
 * 工单统计（后端聚合接口 + alova 30 秒缓存），work/mine 两页共用
 */
export function useTicketStats() {
  const pendingTickets = ref<number | null>(null)
  const processingTickets = ref<number | null>(null)
  const doneTickets = ref<number | null>(null)

  async function loadTicketStats() {
    try {
      const stats = await TicketAPI.getStats()
      pendingTickets.value = stats.pending
      processingTickets.value = stats.processing
      doneTickets.value = stats.done
    }
    catch { /* silent */ }
  }

  return { pendingTickets, processingTickets, doneTickets, loadTicketStats }
}
