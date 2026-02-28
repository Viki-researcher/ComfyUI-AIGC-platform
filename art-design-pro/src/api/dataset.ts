import axios from 'axios'
import { useUserStore } from '@/store/modules/user'

export async function fetchExportDataset(projectId: number, format: 'yolo' | 'coco') {
  const { accessToken } = useUserStore()

  const res = await axios.get('/api/dataset/export', {
    params: { project_id: projectId, format },
    responseType: 'blob',
    headers: { Authorization: accessToken || '' }
  })

  const blob = new Blob([res.data], { type: 'application/zip' })
  const disposition = res.headers['content-disposition'] || ''
  const match = disposition.match(/filename="?([^";\s]+)"?/)
  const filename = match ? match[1] : `dataset_${format}_export.zip`

  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}
