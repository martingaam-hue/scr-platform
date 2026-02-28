"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { formatPct } from "@/lib/format"
import {
  useMyBadges, useProjectBadges, useProjectQuests,
  useGamificationProgress, useLeaderboard,
  RARITY_STYLE, RARITY_TEXT,
} from "@/lib/gamification"
import {
  Trophy, Star, Zap, Target, ChevronRight, Award,
  TrendingUp, Users, CheckCircle, Lock, Flame
} from "lucide-react"

export default function GamificationPage() {
  const queryClient = useQueryClient()
  const [projectId, setProjectId] = useState("")
  const [activeTab, setActiveTab] = useState<"badges" | "quests" | "leaderboard">("badges")

  const { data: myBadges = [] } = useMyBadges()
  const { data: projectBadges = [] } = useProjectBadges(projectId)
  const badges = projectId ? projectBadges : myBadges

  const { data: quests = [] } = useProjectQuests(projectId)
  const { data: progress } = useGamificationProgress(projectId || undefined)
  const { data: leaderboard = [] } = useLeaderboard()

  const completeQuestMutation = useMutation({
    mutationFn: (questId: string) => api.post(`/gamification/quests/${questId}/complete`).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quests"] })
      queryClient.invalidateQueries({ queryKey: ["gamification-progress"] })
      queryClient.invalidateQueries({ queryKey: ["badges"] })
    },
  })

  const earnedBadges = badges.filter(b => b.is_earned)
  const lockedBadges = badges.filter(b => !b.is_earned)

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Trophy className="h-7 w-7 text-amber-500" />
          Investor Readiness Score
        </h1>
        <p className="text-sm text-gray-500 mt-1">Earn badges, complete quests, and climb the leaderboard</p>
      </div>

      {/* Project selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">Project</label>
        <input
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-64"
          placeholder="Paste project UUID…"
          value={projectId}
          onChange={e => setProjectId(e.target.value)}
        />
      </div>

      {/* Progress card */}
      {progress && (
        <div className="rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 to-yellow-50 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm font-medium text-amber-700">Current Level</p>
              <p className="text-3xl font-bold text-amber-900">{progress.level}</p>
            </div>
            {progress.score != null && (
              <div className="text-right">
                <p className="text-sm font-medium text-amber-700">Signal Score</p>
                <p className="text-3xl font-bold text-amber-900">{progress.score.toFixed(0)}</p>
              </div>
            )}
            <div className="text-right">
              <p className="text-sm font-medium text-amber-700">Total Points</p>
              <p className="text-3xl font-bold text-amber-900">{progress.total_points.toLocaleString()}</p>
            </div>
          </div>
          {progress.next_milestone != null && (
            <div>
              <div className="flex justify-between text-xs text-amber-700 mb-1">
                <span>Progress to next milestone</span>
                <span>{Math.round(progress.progress_to_next)}%</span>
              </div>
              <div className="h-3 bg-amber-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-amber-500 rounded-full transition-all"
                  style={{ width: `${Math.min(100, progress.progress_to_next)}%` }}
                />
              </div>
            </div>
          )}
          <div className="flex items-center gap-6 mt-3 text-sm text-amber-700">
            <span className="flex items-center gap-1"><Award className="h-4 w-4" />{progress.badge_count} badges</span>
            <span className="flex items-center gap-1"><Target className="h-4 w-4" />{progress.active_quests} active quests</span>
            {progress.rank && <span className="flex items-center gap-1"><Trophy className="h-4 w-4" />Rank #{progress.rank}</span>}
          </div>
        </div>
      )}

      {/* Stats row (if no project) */}
      {!progress && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Badges Earned", value: earnedBadges.length, icon: Award, color: "text-amber-600", bg: "bg-amber-50 border-amber-200" },
            { label: "Total Points", value: earnedBadges.reduce((s, b) => s + b.points, 0).toLocaleString(), icon: Star, color: "text-purple-600", bg: "bg-purple-50 border-purple-200" },
            { label: "Leaderboard", value: `#${leaderboard.findIndex(e => false) + 1 || "—"}`, icon: TrendingUp, color: "text-blue-600", bg: "bg-blue-50 border-blue-200" },
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
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {(["badges", "quests", "leaderboard"] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${activeTab === tab ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
          >
            {tab}
            {tab === "quests" && quests.length > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 rounded-full text-xs bg-primary-100 text-primary-700">{quests.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Badge showcase */}
      {activeTab === "badges" && (
        <div className="space-y-6">
          {earnedBadges.length > 0 && (
            <div>
              <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Earned ({earnedBadges.length})
              </h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {earnedBadges.map(badge => (
                  <div key={badge.id} className={`rounded-xl border p-4 text-center ${RARITY_STYLE[badge.rarity] ?? "border-gray-200 bg-gray-50"}`}>
                    <div className="text-3xl mb-2">{badge.icon}</div>
                    <p className="font-semibold text-gray-900 text-sm">{badge.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{badge.description}</p>
                    <div className="flex items-center justify-center gap-2 mt-2">
                      <span className={`text-xs font-medium capitalize ${RARITY_TEXT[badge.rarity] ?? "text-gray-500"}`}>{badge.rarity}</span>
                      <span className="text-xs text-amber-600 font-medium flex items-center gap-0.5">
                        <Star className="h-3 w-3" />{badge.points}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {lockedBadges.length > 0 && (
            <div>
              <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Lock className="h-4 w-4 text-gray-400" />
                Locked ({lockedBadges.length})
              </h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {lockedBadges.map(badge => (
                  <div key={badge.id} className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 text-center opacity-60">
                    <div className="text-3xl mb-2 grayscale">{badge.icon}</div>
                    <p className="font-semibold text-gray-700 text-sm">{badge.name}</p>
                    <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{badge.description}</p>
                    <div className="flex items-center justify-center gap-2 mt-2">
                      <Lock className="h-3 w-3 text-gray-300" />
                      <span className="text-xs text-gray-400 capitalize">{badge.rarity}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {badges.length === 0 && (
            <div className="text-center py-12 border border-dashed border-gray-300 rounded-xl text-gray-500">
              <Trophy className="h-10 w-10 text-gray-300 mx-auto mb-3" />
              <p className="font-medium">No badges yet</p>
              <p className="text-sm mt-1">Complete quests and improve your signal score to earn badges</p>
            </div>
          )}
        </div>
      )}

      {/* Quests */}
      {activeTab === "quests" && (
        <div className="space-y-3">
          {!projectId && (
            <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-700">
              Enter a Project ID above to see project-specific quests
            </div>
          )}
          {quests.map(quest => (
            <div key={quest.id} className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-50 flex-shrink-0">
                  <Flame className="h-5 w-5 text-primary-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900">{quest.title}</p>
                  <p className="text-sm text-gray-500 mt-0.5">{quest.description}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <TrendingUp className="h-3.5 w-3.5 text-green-500" />
                      +{quest.estimated_score_impact} score impact
                    </span>
                    {quest.reward_badge_name && (
                      <span className="flex items-center gap-1">
                        <Award className="h-3.5 w-3.5 text-amber-500" />
                        Earns: {quest.reward_badge_name}
                      </span>
                    )}
                  </div>
                </div>
                {quest.status === "active" && (
                  <button
                    onClick={() => completeQuestMutation.mutate(quest.id)}
                    disabled={completeQuestMutation.isPending}
                    className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Complete
                  </button>
                )}
                {quest.status === "completed" && (
                  <span className="flex-shrink-0 flex items-center gap-1 text-green-600 text-sm font-medium">
                    <CheckCircle className="h-4 w-4" /> Done
                  </span>
                )}
              </div>
            </div>
          ))}
          {projectId && quests.length === 0 && (
            <div className="text-center py-12 border border-dashed border-gray-300 rounded-xl text-gray-500">
              <Target className="h-10 w-10 text-gray-300 mx-auto mb-3" />
              <p className="font-medium">No active quests</p>
              <p className="text-sm mt-1">All quests completed — great work!</p>
            </div>
          )}
        </div>
      )}

      {/* Leaderboard */}
      {activeTab === "leaderboard" && (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead className="text-xs uppercase text-gray-500 bg-gray-50 border-b">
              <tr>
                <th className="px-5 py-3 text-left">Rank</th>
                <th className="px-5 py-3 text-left">Project</th>
                <th className="px-5 py-3 text-left">Organisation</th>
                <th className="px-5 py-3 text-right">Score</th>
                <th className="px-5 py-3 text-right">Badges</th>
                <th className="px-5 py-3 text-right">Points</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {leaderboard.map((entry) => (
                <tr key={entry.rank} className={`hover:bg-gray-50 ${entry.rank <= 3 ? "bg-amber-50/30" : ""}`}>
                  <td className="px-5 py-3">
                    <span className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${entry.rank === 1 ? "bg-amber-400 text-white" : entry.rank === 2 ? "bg-gray-300 text-gray-700" : entry.rank === 3 ? "bg-orange-300 text-white" : "bg-gray-100 text-gray-600"}`}>
                      {entry.rank}
                    </span>
                  </td>
                  <td className="px-5 py-3 font-medium text-gray-900">{entry.project_name}</td>
                  <td className="px-5 py-3 text-gray-500">{entry.org_name}</td>
                  <td className="px-5 py-3 text-right font-semibold text-gray-900">{entry.score.toFixed(0)}</td>
                  <td className="px-5 py-3 text-right text-gray-700">{entry.badge_count}</td>
                  <td className="px-5 py-3 text-right font-medium text-amber-600">{entry.total_points.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {leaderboard.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <Users className="h-10 w-10 text-gray-300 mx-auto mb-3" />
              <p className="font-medium">Leaderboard is empty</p>
              <p className="text-sm mt-1">Opt-in via your profile settings to appear here</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
