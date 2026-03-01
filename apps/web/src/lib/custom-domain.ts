import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"

export interface CustomDomainRecord {
  id: string
  org_id: string
  domain: string
  status: "pending" | "verifying" | "verified" | "failed" | "active"
  cname_target: string
  verification_token: string
  verified_at: string | null
  ssl_provisioned_at: string | null
  last_checked_at: string | null
  error_message: string | null
  created_at: string
  dns_instructions: {
    cname_record: { type: string; name: string; value: string; ttl: number }
    txt_record: { type: string; name: string; value: string; ttl: number }
    note: string
  }
}

export const useCustomDomain = () =>
  useQuery<CustomDomainRecord | null>({
    queryKey: ["custom-domain"],
    queryFn: async () => {
      const { data } = await api.get("/custom-domain")
      return data
    },
  })

export const useSetDomain = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (domain: string) => api.put("/custom-domain", { domain }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["custom-domain"] }),
  })
}

export const useVerifyDomain = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post("/custom-domain/verify"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["custom-domain"] }),
  })
}

export const useDeleteDomain = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.delete("/custom-domain"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["custom-domain"] }),
  })
}
