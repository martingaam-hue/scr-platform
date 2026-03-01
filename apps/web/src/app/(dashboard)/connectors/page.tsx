"use client"

import { useState } from "react"
import {
  useConnectors, useConnectorConfigs, useConnectorUsage,
  useEnableConnector, useDisableConnector, useTestConnector,
  CATEGORY_COLORS, TIER_BADGE,
} from "@/lib/connectors"
import {
  Plug, CheckCircle, XCircle, AlertCircle, ToggleLeft, ToggleRight,
  Activity, Clock, Eye, EyeOff, RefreshCw
} from "lucide-react"

export default function ConnectorsPage() {
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({})
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({})
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; message: string } | null>>({})

  const { data: connectors = [] } = useConnectors()
  const { data: configs = [] } = useConnectorConfigs()
  const { data: usageData = [] } = useConnectorUsage()

  const enableMutation = useEnableConnector()
  const disableMutation = useDisableConnector()
  const testMutation = useTestConnector()

  const configMap = Object.fromEntries(configs.map(c => [c.connector_id, c]))
  const usageMap = Object.fromEntries(usageData.map(u => [u.connector_id, u]))

  const totalEnabledConnectors = configs.filter(c => c.is_enabled).length
  const totalCallsToday = usageData.reduce((sum, u) => sum + u.calls_today, 0)
  const totalErrorRate = usageData.length > 0
    ? (usageData.reduce((sum, u) => sum + u.error_calls, 0) / Math.max(1, usageData.reduce((sum, u) => sum + u.total_calls, 0)) * 100)
    : 0

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">API Connectors</h1>
        <p className="text-sm text-gray-500 mt-1">Third-party data integrations for enriched deal intelligence</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Active Connectors", value: totalEnabledConnectors, icon: Plug, color: "text-primary-600", bg: "bg-primary-50 border-primary-200" },
          { label: "API Calls Today", value: totalCallsToday.toLocaleString(), icon: Activity, color: "text-blue-600", bg: "bg-blue-50 border-blue-200" },
          { label: "Error Rate", value: `${totalErrorRate.toFixed(1)}%`, icon: AlertCircle, color: totalErrorRate > 5 ? "text-red-600" : "text-green-600", bg: totalErrorRate > 5 ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200" },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className={`rounded-xl border p-4 ${bg}`}>
            <div className="flex items-center gap-2">
              <Icon className={`h-5 w-5 ${color}`} />
              <span className="text-sm font-medium text-gray-700">{label}</span>
            </div>
            <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Connector catalog */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {connectors.map((connector) => {
          const config = configMap[connector.id]
          const usage = usageMap[connector.id]
          const isEnabled = config?.is_enabled ?? false
          const testResult = testResults[connector.id]
          const showKey = showKeys[connector.id] ?? false
          const apiKey = apiKeys[connector.id] ?? ""

          return (
            <div key={connector.id} className={`rounded-xl border bg-white p-5 space-y-4 ${isEnabled ? "border-primary-200" : "border-gray-200"}`}>
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg ${isEnabled ? "bg-primary-100" : "bg-gray-100"}`}>
                    <Plug className={`h-5 w-5 ${isEnabled ? "text-primary-600" : "text-gray-400"}`} />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">{connector.display_name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${CATEGORY_COLORS[connector.category] ?? "bg-gray-100 text-gray-600"}`}>
                        {connector.category.replace(/_/g, " ")}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${TIER_BADGE[connector.pricing_tier] ?? "bg-gray-100 text-gray-600"}`}>
                        {connector.pricing_tier}
                      </span>
                    </div>
                  </div>
                </div>
                {/* Toggle */}
                <button
                  onClick={() => {
                    if (isEnabled) {
                      disableMutation.mutate(connector.id)
                    } else {
                      enableMutation.mutate({ id: connector.id, apiKey })
                    }
                  }}
                  className="flex-shrink-0"
                >
                  {isEnabled
                    ? <ToggleRight className="h-8 w-8 text-primary-600" />
                    : <ToggleLeft className="h-8 w-8 text-gray-300" />
                  }
                </button>
              </div>

              {/* API Key input */}
              {connector.auth_type === "api_key" && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">API Key</label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type={showKey ? "text" : "password"}
                        className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm pr-8"
                        placeholder="Paste your API key…"
                        value={apiKey}
                        onChange={e => setApiKeys(prev => ({ ...prev, [connector.id]: e.target.value }))}
                      />
                      <button
                        onClick={() => setShowKeys(prev => ({ ...prev, [connector.id]: !showKey }))}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    <button
                      onClick={() => testMutation.mutate(connector.id, {
                        onSuccess: (data) => setTestResults(prev => ({ ...prev, [connector.id]: { ok: data.ok, message: data.message } })),
                        onError: () => setTestResults(prev => ({ ...prev, [connector.id]: { ok: false, message: "Connection failed" } })),
                      })}
                      disabled={testMutation.isPending}
                      className="flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg text-xs hover:bg-gray-50 disabled:opacity-50"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${testMutation.isPending ? "animate-spin" : ""}`} />
                      Test
                    </button>
                  </div>
                  {testResult && (
                    <div className={`flex items-center gap-1 mt-1 text-xs ${testResult.ok ? "text-green-600" : "text-red-600"}`}>
                      {testResult.ok ? <CheckCircle className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                      {testResult.message}
                    </div>
                  )}
                </div>
              )}

              {/* Usage stats */}
              {usage && (
                <div className="grid grid-cols-3 gap-3 pt-2 border-t border-gray-100">
                  <div>
                    <p className="text-xs text-gray-500">Calls (month)</p>
                    <p className="text-sm font-semibold text-gray-900">{usage.total_calls.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Avg latency</p>
                    <p className="text-sm font-semibold text-gray-900">{Math.round(usage.avg_response_ms)}ms</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Error rate</p>
                    <p className={`text-sm font-semibold ${usage.error_calls / Math.max(1, usage.total_calls) > 0.05 ? "text-red-600" : "text-green-600"}`}>
                      {(usage.error_calls / Math.max(1, usage.total_calls) * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
              )}

              {/* Rate limit info */}
              <div className="flex items-center gap-1.5 text-xs text-gray-400">
                <Clock className="h-3.5 w-3.5" />
                <span>{connector.rate_limit_per_minute} req/min · {connector.auth_type.replace("_", " ")}</span>
              </div>
            </div>
          )
        })}
      </div>

      {connectors.length === 0 && (
        <div className="text-center py-12 border border-dashed border-gray-300 rounded-xl text-gray-500">
          <Plug className="h-10 w-10 text-gray-300 mx-auto mb-3" />
          <p className="font-medium">No connectors available</p>
          <p className="text-sm mt-1">Contact your administrator to add data connectors</p>
        </div>
      )}
    </div>
  )
}
