"use client"

import { useState } from "react"
import { formatDate } from "@/lib/format"
import {
  useDealRooms, useRoomMessages, useRoomActivity,
  useCreateRoom, useInviteMember, useSendMessage,
  type DealRoom, type DealRoomMessage, type DealRoomActivity,
} from "@/lib/deal-rooms"
import { useProjectQuestions, useCreateQuestion, useQAStats } from "@/lib/qa"
import { usePlatformModeStore } from "@/lib/store"
import {
  Users, MessageSquare, Plus, X, Send,
  Lock, Eye, Activity, HelpCircle,
  Handshake, TrendingUp, Building2, Leaf,
  DollarSign, Zap, CheckCircle2, Clock,
  ChevronDown, ChevronUp, Target,
} from "lucide-react"

const STATUS_BADGE: Record<string, string> = {
  active:  "bg-green-100 text-green-700",
  closed:  "bg-gray-100 text-gray-500",
  pending: "bg-yellow-100 text-yellow-700",
}

// ── Investor-side mock data ────────────────────────────────────────────────

const MOCK_ROOMS: DealRoom[] = [
  {
    id: "room-p2",
    name: "Danube Hydro Expansion — Due Diligence",
    project_id: "p2",
    status: "active",
    created_by: "user-sofia",
    settings: { nda_required: true, download_restricted: false },
    members: [
      { id: "mbr-1", room_id: "room-p2", user_id: "user-sofia",  email: "sofia.bergman@fund.eu",    role: "admin",  org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-10T09:00:00Z", joined_at: "2026-02-10T09:00:00Z", nda_signed_at: "2026-02-10T09:05:00Z" },
      { id: "mbr-2", room_id: "room-p2", user_id: "user-marco",  email: "marco.rossi@fund.eu",      role: "member", org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-10T09:10:00Z", joined_at: "2026-02-10T10:00:00Z", nda_signed_at: "2026-02-10T10:00:00Z" },
      { id: "mbr-3", room_id: "room-p2", user_id: "user-danube", email: "ceo@danubehydro.ro",       role: "member", org_name: "Danube Hydro SA",          permissions: {}, invited_at: "2026-02-11T08:00:00Z", joined_at: "2026-02-11T09:00:00Z", nda_signed_at: "2026-02-11T09:05:00Z" },
    ],
    created_at: "2026-02-10T09:00:00Z",
  },
  {
    id: "room-p3",
    name: "Aegean Wind Cluster — Due Diligence",
    project_id: "p3",
    status: "active",
    created_by: "user-erik",
    settings: { nda_required: true, download_restricted: true },
    members: [
      { id: "mbr-4", room_id: "room-p3", user_id: "user-erik",   email: "erik.lindstrom@fund.eu",   role: "admin",  org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-15T10:00:00Z", joined_at: "2026-02-15T10:00:00Z", nda_signed_at: "2026-02-15T10:05:00Z" },
      { id: "mbr-5", room_id: "room-p3", user_id: "user-sofia",  email: "sofia.bergman@fund.eu",    role: "member", org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-15T10:10:00Z", joined_at: "2026-02-15T11:00:00Z", nda_signed_at: "2026-02-15T11:05:00Z" },
      { id: "mbr-6", room_id: "room-p3", user_id: "user-aegean", email: "ir@aegeanwind.gr",         role: "member", org_name: "Aegean Wind GmbH",         permissions: {}, invited_at: "2026-02-16T08:00:00Z", joined_at: "2026-02-16T09:30:00Z", nda_signed_at: "2026-02-16T09:35:00Z" },
    ],
    created_at: "2026-02-15T10:00:00Z",
  },
  {
    id: "room-p4",
    name: "Bavarian Biomass Network — Negotiation",
    project_id: "p4",
    status: "active",
    created_by: "user-marco",
    settings: { nda_required: false, download_restricted: false },
    members: [
      { id: "mbr-7", room_id: "room-p4", user_id: "user-marco",   email: "marco.rossi@fund.eu",     role: "admin",  org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-20T09:00:00Z", joined_at: "2026-02-20T09:00:00Z", nda_signed_at: null },
      { id: "mbr-8", room_id: "room-p4", user_id: "user-erik",    email: "erik.lindstrom@fund.eu",  role: "member", org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-20T09:10:00Z", joined_at: "2026-02-20T10:00:00Z", nda_signed_at: null },
      { id: "mbr-9", room_id: "room-p4", user_id: "user-bavarian",email: "cfo@bavarianbiomass.de",  role: "member", org_name: "Bavarian Biomass GmbH",    permissions: {}, invited_at: "2026-02-21T08:00:00Z", joined_at: "2026-02-21T09:00:00Z", nda_signed_at: null },
    ],
    created_at: "2026-02-20T09:00:00Z",
  },
]

const MOCK_MESSAGES: Record<string, DealRoomMessage[]> = {
  "room-p2": [
    { id: "msg-1", room_id: "room-p2", user_id: "user-sofia",  parent_id: null, content: "Welcome to the Danube Hydro DD room. Please upload the latest hydrology report and grid connection permit by end of week.", mentions: [], created_at: "2026-02-10T09:15:00Z" },
    { id: "msg-2", room_id: "room-p2", user_id: "user-danube", parent_id: null, content: "Thank you. We will upload the Q4 2025 hydrology study and the ANRE grid permit today. The technical report from Bureau Veritas will follow Thursday.", mentions: [], created_at: "2026-02-10T11:30:00Z" },
    { id: "msg-3", room_id: "room-p2", user_id: "user-marco",  parent_id: null, content: "I have reviewed the P50/P90 yield study. The P50 annual generation is 142 GWh which is in line with our assumptions. Can you confirm the curtailment assumptions used?", mentions: [], created_at: "2026-02-12T14:00:00Z" },
    { id: "msg-4", room_id: "room-p2", user_id: "user-danube", parent_id: null, content: "Curtailment is modelled at 3.2% based on the 2024 grid operator report for the Craiova substation. We have the detailed model available for sharing.", mentions: [], created_at: "2026-02-12T15:45:00Z" },
    { id: "msg-5", room_id: "room-p2", user_id: "user-sofia",  parent_id: null, content: "DD checklist is now 65% complete. Outstanding items: environmental permit, land title registry, and offtake term sheet. Target completion: 5 March.", mentions: [], created_at: "2026-03-01T10:00:00Z" },
  ],
  "room-p3": [
    { id: "msg-6", room_id: "room-p3", user_id: "user-erik",   parent_id: null, content: "Aegean Wind room is open. We are targeting IC submission by 28 March. Key focus areas: turbine supply chain, grid capacity, and permitting timeline.", mentions: [], created_at: "2026-02-15T10:30:00Z" },
    { id: "msg-7", room_id: "room-p3", user_id: "user-aegean", parent_id: null, content: "Site visit has been scheduled for 4 March at 09:00 local time. We will arrange transport from Athens airport. Please confirm attendee names for permits.", mentions: [], created_at: "2026-02-16T09:00:00Z" },
    { id: "msg-8", room_id: "room-p3", user_id: "user-sofia",  parent_id: null, content: "Erik and I will attend. Marco will join remotely. We are also requesting the RWE technical advisor to join for the turbine foundation inspection.", mentions: [], created_at: "2026-02-16T11:00:00Z" },
    { id: "msg-9", room_id: "room-p3", user_id: "user-aegean", parent_id: null, content: "Understood. Term sheet draft has been shared via the data room. Section 4.2 on development fee recoverability is open for discussion.", mentions: [], created_at: "2026-03-02T14:00:00Z" },
    { id: "msg-10", room_id: "room-p3", user_id: "user-erik",  parent_id: null, content: "We reviewed section 4.2. The development fee cap of €1.8M is acceptable subject to a milestone-linked disbursement schedule. We will provide redlines by Friday.", mentions: [], created_at: "2026-03-03T09:30:00Z" },
  ],
  "room-p4": [
    { id: "msg-11", room_id: "room-p4", user_id: "user-marco",   parent_id: null, content: "Bavarian Biomass negotiation room is now active. We have agreed the headline terms. This room is for finalising the SPA and ancillary documents.", mentions: [], created_at: "2026-02-20T09:15:00Z" },
    { id: "msg-12", room_id: "room-p4", user_id: "user-bavarian",parent_id: null, content: "Understood. Our legal team (Noerr München) will upload the first draft SPA by 25 February. Key open items: change of control consent and biomass supply warranties.", mentions: [], created_at: "2026-02-20T11:00:00Z" },
    { id: "msg-13", room_id: "room-p4", user_id: "user-erik",    parent_id: null, content: "We engaged Linklaters on our side. They will revert within 5 business days on the SPA draft. The biomass supply warranties are a key risk point for us — we need a 10-year indexed supply contract.", mentions: [], created_at: "2026-02-21T10:00:00Z" },
    { id: "msg-14", room_id: "room-p4", user_id: "user-bavarian",parent_id: null, content: "We have a 7-year supply agreement in place with Bayerische Holzwerke. Extension option for 5 years at pre-agreed index. Full contract is uploaded in folder /Legal.", mentions: [], created_at: "2026-02-25T14:00:00Z" },
  ],
}

const MOCK_ACTIVITIES: Record<string, DealRoomActivity[]> = {
  "room-p2": [
    { id: "act-1", room_id: "room-p2", user_id: "user-danube", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-1", description: "Uploaded Q4 2025 Hydrology Study", created_at: "2026-02-11T10:00:00Z" },
    { id: "act-2", room_id: "room-p2", user_id: "user-danube", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-2", description: "Uploaded ANRE Grid Connection Permit", created_at: "2026-02-11T14:00:00Z" },
    { id: "act-3", room_id: "room-p2", user_id: "user-marco",  activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-1", description: "Viewed hydrology study (12 min)", created_at: "2026-02-13T09:30:00Z" },
    { id: "act-4", room_id: "room-p2", user_id: "user-danube", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-3", description: "Uploaded Bureau Veritas Technical Report", created_at: "2026-02-13T16:00:00Z" },
  ],
  "room-p3": [
    { id: "act-5", room_id: "room-p3", user_id: "user-aegean", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-4", description: "Uploaded Wind Resource Assessment (WRA)", created_at: "2026-02-17T09:00:00Z" },
    { id: "act-6", room_id: "room-p3", user_id: "user-erik",   activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-4", description: "Viewed WRA report (28 min)", created_at: "2026-02-17T14:00:00Z" },
    { id: "act-7", room_id: "room-p3", user_id: "user-aegean", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-5", description: "Uploaded Term Sheet Draft v1", created_at: "2026-03-02T13:00:00Z" },
  ],
  "room-p4": [
    { id: "act-8",  room_id: "room-p4", user_id: "user-bavarian",activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-6", description: "Uploaded SPA First Draft", created_at: "2026-02-25T10:00:00Z" },
    { id: "act-9",  room_id: "room-p4", user_id: "user-erik",    activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-6", description: "Viewed SPA draft (45 min)", created_at: "2026-02-25T15:00:00Z" },
    { id: "act-10", room_id: "room-p4", user_id: "user-bavarian",activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-7", description: "Uploaded Biomass Supply Agreement", created_at: "2026-02-25T16:00:00Z" },
  ],
}

// ── Ally-side mock data ────────────────────────────────────────────────────

const MOCK_ALLY_ROOMS: DealRoom[] = [
  {
    id: "ally-room-1",
    name: "Porto Solar Park — Investor Interest",
    project_id: "p1",
    status: "active",
    created_by: "user-nordic-cap",
    settings: { nda_required: true, download_restricted: false },
    members: [
      { id: "am-1", room_id: "ally-room-1", user_id: "user-nordic-cap", email: "deals@nordiccap.eu",      role: "admin",  org_name: "Nordic Capital Partners",  permissions: {}, invited_at: "2026-03-01T09:00:00Z", joined_at: "2026-03-01T09:00:00Z", nda_signed_at: "2026-03-01T09:10:00Z" },
      { id: "am-2", room_id: "ally-room-1", user_id: "user-ally-porto", email: "ir@portosolar.pt",        role: "member", org_name: "Porto Solar SA",           permissions: {}, invited_at: "2026-03-01T10:00:00Z", joined_at: "2026-03-01T10:30:00Z", nda_signed_at: "2026-03-01T10:35:00Z" },
      { id: "am-3", room_id: "ally-room-1", user_id: "user-iberian",   email: "iberian@greenventures.es", role: "member", org_name: "Iberian Green Ventures",   permissions: {}, invited_at: "2026-03-02T08:00:00Z", joined_at: "2026-03-02T09:00:00Z", nda_signed_at: "2026-03-02T09:05:00Z" },
    ],
    created_at: "2026-03-01T09:00:00Z",
  },
  {
    id: "ally-room-2",
    name: "Aegean Wind Cluster — Term Sheet Discussion",
    project_id: "p3",
    status: "active",
    created_by: "user-aegean",
    settings: { nda_required: true, download_restricted: true },
    members: [
      { id: "am-4", room_id: "ally-room-2", user_id: "user-aegean",     email: "ir@aegeanwind.gr",          role: "admin",  org_name: "Aegean Wind GmbH",         permissions: {}, invited_at: "2026-02-20T10:00:00Z", joined_at: "2026-02-20T10:00:00Z", nda_signed_at: "2026-02-20T10:05:00Z" },
      { id: "am-5", room_id: "ally-room-2", user_id: "user-euro-infra", email: "team@euroinfra.lu",          role: "member", org_name: "EuroInfra Capital",        permissions: {}, invited_at: "2026-02-20T11:00:00Z", joined_at: "2026-02-20T12:00:00Z", nda_signed_at: "2026-02-20T12:05:00Z" },
      { id: "am-6", room_id: "ally-room-2", user_id: "user-hellas-pe",  email: "deals@hellaspe.gr",          role: "member", org_name: "Hellas Private Equity",    permissions: {}, invited_at: "2026-02-21T08:00:00Z", joined_at: "2026-02-21T09:00:00Z", nda_signed_at: "2026-02-21T09:10:00Z" },
    ],
    created_at: "2026-02-20T10:00:00Z",
  },
  {
    id: "ally-room-3",
    name: "Alpine Hydro Partners — Strategic Partnership",
    project_id: "p5",
    status: "active",
    created_by: "user-alpine",
    settings: { nda_required: false, download_restricted: false },
    members: [
      { id: "am-7", room_id: "ally-room-3", user_id: "user-alpine",     email: "ceo@alpinehydro.ch",         role: "admin",  org_name: "Alpine Hydro Partners",   permissions: {}, invited_at: "2026-03-05T09:00:00Z", joined_at: "2026-03-05T09:00:00Z", nda_signed_at: null },
      { id: "am-8", room_id: "ally-room-3", user_id: "user-swiss-re",   email: "infra@swissreinfra.ch",      role: "member", org_name: "Swiss Re Infrastructure", permissions: {}, invited_at: "2026-03-05T10:00:00Z", joined_at: "2026-03-05T11:00:00Z", nda_signed_at: null },
      { id: "am-9", room_id: "ally-room-3", user_id: "user-zurich-pen", email: "pm@zurichpension.ch",         role: "member", org_name: "Zürich Pension Group",    permissions: {}, invited_at: "2026-03-06T08:00:00Z", joined_at: "2026-03-06T09:00:00Z", nda_signed_at: null },
    ],
    created_at: "2026-03-05T09:00:00Z",
  },
]

const MOCK_ALLY_MESSAGES: Record<string, DealRoomMessage[]> = {
  "ally-room-1": [
    { id: "am-msg-1", room_id: "ally-room-1", user_id: "user-nordic-cap", parent_id: null, content: "We reviewed the Porto Solar Park prospectus and are very interested in exploring a co-investment structure. Our infrastructure fund has a €250M allocation for Iberian solar and Porto would fit well. Can we schedule a call this week?", mentions: [], created_at: "2026-03-01T09:30:00Z" },
    { id: "am-msg-2", room_id: "ally-room-1", user_id: "user-ally-porto", parent_id: null, content: "Thank you for reaching out. We would be delighted to discuss further. We are available Wednesday 3pm CET or Thursday morning. The project is currently at RTB stage with a PPA term sheet under negotiation with EDP.", mentions: [], created_at: "2026-03-01T11:00:00Z" },
    { id: "am-msg-3", room_id: "ally-room-1", user_id: "user-nordic-cap", parent_id: null, content: "Wednesday 3pm CET works for us. We will prepare a preliminary investment thesis. Quick questions ahead of the call: (1) What equity split are you targeting? (2) Is there flexibility on the development fee structure?", mentions: [], created_at: "2026-03-01T14:00:00Z" },
    { id: "am-msg-4", room_id: "ally-room-1", user_id: "user-iberian",    parent_id: null, content: "We at Iberian Green Ventures are also following this project closely. We have existing grid connection rights in the Alentejo region which could be a valuable synergy for Porto Solar. Happy to discuss co-development options.", mentions: [], created_at: "2026-03-02T09:30:00Z" },
    { id: "am-msg-5", room_id: "ally-room-1", user_id: "user-ally-porto", parent_id: null, content: "Excellent — the Alentejo grid rights are exactly what we have been exploring. We are targeting 40% equity at the project level and 15% co-development to strategic partners. We will circulate the full information pack and financial model ahead of Wednesday's call.", mentions: [], created_at: "2026-03-02T11:30:00Z" },
  ],
  "ally-room-2": [
    { id: "am-msg-6", room_id: "ally-room-2", user_id: "user-euro-infra", parent_id: null, content: "EuroInfra Capital has completed initial screening on the Aegean Wind Cluster and we are ready to progress to binding terms. Our IC has approved a ticket size of €45–65M for the senior equity tranche.", mentions: [], created_at: "2026-02-20T12:30:00Z" },
    { id: "am-msg-7", room_id: "ally-room-2", user_id: "user-aegean",     parent_id: null, content: "This is very encouraging. We are also in parallel discussions with Hellas PE on a mezzanine tranche. The key terms we would like to align on are: (1) governance rights at board level, (2) distribution waterfall, (3) development fee crystallisation at financial close.", mentions: [], created_at: "2026-02-20T15:00:00Z" },
    { id: "am-msg-8", room_id: "ally-room-2", user_id: "user-hellas-pe",  parent_id: null, content: "Hellas PE here — we are comfortable with a €15M mezzanine position at EURIBOR + 650bps. Governance: we would need one observer seat and standard minority protections. Happy to coordinate with EuroInfra on the cap table.", mentions: [], created_at: "2026-02-21T09:00:00Z" },
    { id: "am-msg-9", room_id: "ally-room-2", user_id: "user-aegean",     parent_id: null, content: "Thank you both. We will circulate a revised term sheet by Friday incorporating these parameters. The €80M blended structure — €65M equity + €15M mezz — matches our financing plan. Site visit for EuroInfra team is confirmed for 18 March.", mentions: [], created_at: "2026-02-22T10:00:00Z" },
    { id: "am-msg-10", room_id: "ally-room-2", user_id: "user-euro-infra", parent_id: null, content: "Confirmed for 18 March. Please also prepare a presentation on curtailment risk mitigation — this was a concern raised by our risk committee given the REPowerEU grid constraints in the Aegean region.", mentions: [], created_at: "2026-02-23T14:00:00Z" },
  ],
  "ally-room-3": [
    { id: "am-msg-11", room_id: "ally-room-3", user_id: "user-swiss-re",   parent_id: null, content: "Swiss Re Infrastructure is exploring a long-term strategic partnership with Alpine Hydro. We see significant potential for a 25-year inflation-linked offtake and balance sheet capacity for the expansion programme.", mentions: [], created_at: "2026-03-05T11:00:00Z" },
    { id: "am-msg-12", room_id: "ally-room-3", user_id: "user-alpine",     parent_id: null, content: "A long-term strategic partnership is exactly our vision for Phase 2. The 240 MW expansion plan requires a cornerstone investor with a long hold period. The inflation-linked offtake structure aligns well with our revenue model.", mentions: [], created_at: "2026-03-05T13:00:00Z" },
    { id: "am-msg-13", room_id: "ally-room-3", user_id: "user-zurich-pen", parent_id: null, content: "Zürich Pension Group would consider a co-investment alongside Swiss Re. We have a €500M Article 9 mandate and Alpine Hydro's ESG profile — particularly the biodiversity corridor initiative — makes this a compelling fit for our impact allocation.", mentions: [], created_at: "2026-03-06T09:30:00Z" },
    { id: "am-msg-14", room_id: "ally-room-3", user_id: "user-alpine",     parent_id: null, content: "Wonderful. We are preparing a full investor pack including the biodiversity impact study and the updated 10-year cash flow model. We would like to propose a 3-party alignment meeting at our Zurich office — does the week of 17 March work?", mentions: [], created_at: "2026-03-06T14:00:00Z" },
  ],
}

const MOCK_ALLY_ACTIVITIES: Record<string, DealRoomActivity[]> = {
  "ally-room-1": [
    { id: "aa-1", room_id: "ally-room-1", user_id: "user-nordic-cap", activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-ps-1", description: "Viewed Porto Solar prospectus (22 min)", created_at: "2026-03-01T08:30:00Z" },
    { id: "aa-2", room_id: "ally-room-1", user_id: "user-ally-porto", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-ps-2", description: "Uploaded PPA term sheet — EDP Renewables", created_at: "2026-03-02T10:00:00Z" },
    { id: "aa-3", room_id: "ally-room-1", user_id: "user-nordic-cap", activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-ps-2", description: "Viewed PPA term sheet (18 min)", created_at: "2026-03-02T14:30:00Z" },
    { id: "aa-4", room_id: "ally-room-1", user_id: "user-iberian",    activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-ps-1", description: "Viewed prospectus (35 min)", created_at: "2026-03-02T16:00:00Z" },
  ],
  "ally-room-2": [
    { id: "aa-5", room_id: "ally-room-2", user_id: "user-euro-infra", activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-aw-1", description: "Viewed Aegean Wind financial model (41 min)", created_at: "2026-02-19T15:00:00Z" },
    { id: "aa-6", room_id: "ally-room-2", user_id: "user-aegean",     activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-aw-2", description: "Uploaded revised term sheet draft v2", created_at: "2026-02-22T17:00:00Z" },
    { id: "aa-7", room_id: "ally-room-2", user_id: "user-hellas-pe",  activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-aw-2", description: "Viewed term sheet draft v2 (12 min)", created_at: "2026-02-23T09:00:00Z" },
  ],
  "ally-room-3": [
    { id: "aa-8", room_id: "ally-room-3", user_id: "user-swiss-re",   activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-ah-1", description: "Viewed Alpine Hydro investor pack (55 min)", created_at: "2026-03-04T14:00:00Z" },
    { id: "aa-9", room_id: "ally-room-3", user_id: "user-zurich-pen", activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-ah-1", description: "Viewed investor pack (30 min)", created_at: "2026-03-05T10:00:00Z" },
    { id: "aa-10", room_id: "ally-room-3", user_id: "user-alpine",    activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-ah-2", description: "Uploaded biodiversity impact study 2025", created_at: "2026-03-06T11:00:00Z" },
  ],
}

// ── Synergy data ───────────────────────────────────────────────────────────

interface Synergy {
  id: string
  category: "financial" | "operational" | "strategic" | "esg"
  title: string
  description: string
  potentialValue: string
  status: "identified" | "in_discussion" | "agreed"
}

const MOCK_SYNERGIES: Record<string, Synergy[]> = {
  "ally-room-1": [
    { id: "syn-1", category: "financial",    title: "Co-development equity structure", description: "Nordic Capital's €250M solar mandate aligns with Porto's 40% equity target. Shared development cost structure could reduce CAPEX by 8–12%.", potentialValue: "€18–22M CAPEX reduction", status: "in_discussion" },
    { id: "syn-2", category: "operational",  title: "Alentejo grid connection rights",  description: "Iberian Green Ventures holds existing grid connection rights in Alentejo. Combining with Porto Solar's 180 MW capacity could accelerate grid approval by 14 months.", potentialValue: "14 months faster commissioning", status: "identified" },
    { id: "syn-3", category: "strategic",    title: "Iberian platform co-investment",  description: "Nordic + Iberian co-investment platform could create a 600 MW Iberian solar cluster, unlocking better O&M contracts and PPA pricing.", potentialValue: "€4–6M/year O&M savings", status: "identified" },
    { id: "syn-4", category: "esg",          title: "Shared biodiversity monitoring",  description: "Joint environmental monitoring programme across both investors' Portuguese assets would reduce reporting costs and improve Article 9 compliance.", potentialValue: "€0.3M/year reporting cost reduction", status: "identified" },
  ],
  "ally-room-2": [
    { id: "syn-5", category: "financial",    title: "€80M blended capital structure",  description: "EuroInfra senior equity (€65M) + Hellas PE mezzanine (€15M) achieves target leverage without bank debt during construction phase.", potentialValue: "€80M fully committed", status: "agreed" },
    { id: "syn-6", category: "operational",  title: "REPowerEU grid priority access",  description: "EuroInfra's existing Aegean Sea portfolio creates precedent for grid priority access under REPowerEU framework — applies to Aegean Wind Cluster sites.", potentialValue: "€2.1M/year curtailment risk reduction", status: "in_discussion" },
    { id: "syn-7", category: "strategic",    title: "Greek offshore wind development",  description: "Hellas PE has exclusive development rights on two offshore wind sites adjacent to Aegean Wind. Combined development could create a 850 MW Aegean platform.", potentialValue: "Platform premium: +20–25% exit multiple", status: "identified" },
  ],
  "ally-room-3": [
    { id: "syn-8",  category: "financial",   title: "25-year inflation-linked offtake",  description: "Swiss Re's balance sheet capacity for long-duration infrastructure debt enables a 25-year CPI+50bps offtake — eliminates revenue risk for the expansion.", potentialValue: "100% revenue certainty for 25 years", status: "in_discussion" },
    { id: "syn-9",  category: "esg",         title: "Article 9 impact mandate fit",       description: "Zürich Pension's €500M Article 9 mandate is a direct fit for Alpine Hydro's biodiversity corridor initiative. ESG documentation already in progress.", potentialValue: "€150–200M commitment potential", status: "in_discussion" },
    { id: "syn-10", category: "strategic",   title: "Swiss clean energy platform",        description: "Swiss Re + Zürich Pension co-investment creates a de-facto Swiss clean energy infrastructure platform — Alpine Hydro as anchor asset.", potentialValue: "Platform anchor positioning", status: "identified" },
    { id: "syn-11", category: "operational", title: "Shared hydrology expertise",         description: "Swiss Re's existing Alpine hydro portfolio provides operational benchmarking data that would reduce insurance premiums for Alpine Hydro by an estimated 12%.", potentialValue: "€0.6M/year insurance savings", status: "agreed" },
  ],
}

const SYNERGY_ICONS = {
  financial:   DollarSign,
  operational: Zap,
  strategic:   Target,
  esg:         Leaf,
}

const SYNERGY_COLORS = {
  financial:   { bg: "bg-green-50",   text: "text-green-700",   border: "border-green-200",   icon: "text-green-600" },
  operational: { bg: "bg-blue-50",    text: "text-blue-700",    border: "border-blue-200",    icon: "text-blue-600" },
  strategic:   { bg: "bg-purple-50",  text: "text-purple-700",  border: "border-purple-200",  icon: "text-purple-600" },
  esg:         { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", icon: "text-emerald-600" },
}

const SYNERGY_STATUS_BADGE = {
  identified:    "bg-gray-100 text-gray-600",
  in_discussion: "bg-blue-100 text-blue-700",
  agreed:        "bg-green-100 text-green-700",
}

// Name maps
const INVESTOR_NAMES: Record<string, string> = {
  "user-nordic-cap": "Nordic Capital Partners",
  "user-ally-porto": "Porto Solar SA",
  "user-iberian":    "Iberian Green Ventures",
  "user-euro-infra": "EuroInfra Capital",
  "user-aegean":     "Aegean Wind GmbH",
  "user-hellas-pe":  "Hellas Private Equity",
  "user-alpine":     "Alpine Hydro Partners",
  "user-swiss-re":   "Swiss Re Infrastructure",
  "user-zurich-pen": "Zürich Pension Group",
}

const DEAL_NAMES: Record<string, string> = {
  "user-sofia":    "Sofia Bergman",
  "user-erik":     "Erik Lindström",
  "user-marco":    "Marco Rossi",
  "user-danube":   "Danube Hydro SA",
  "user-aegean":   "Aegean Wind GmbH",
  "user-bavarian": "Bavarian Biomass GmbH",
}

// ── Synergies tab ──────────────────────────────────────────────────────────

function SynergiesTab({ roomId }: { roomId: string }) {
  const synergies = MOCK_SYNERGIES[roomId] ?? []
  const [expanded, setExpanded] = useState<string | null>(null)

  if (synergies.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
        <Handshake className="h-10 w-10 text-gray-200 mx-auto mb-3" />
        <p className="font-medium text-gray-500">No synergies identified yet</p>
        <p className="text-sm text-gray-400 mt-1">Synergies will be surfaced as discussions progress.</p>
      </div>
    )
  }

  const agreed     = synergies.filter(s => s.status === "agreed").length
  const discussing = synergies.filter(s => s.status === "in_discussion").length
  const identified = synergies.filter(s => s.status === "identified").length

  return (
    <div className="space-y-4">
      {/* Stats row */}
      <div className="flex gap-3">
        {[
          { label: "Agreed", count: agreed,     color: "text-green-700 bg-green-50 border-green-200" },
          { label: "In Discussion", count: discussing, color: "text-blue-700 bg-blue-50 border-blue-200" },
          { label: "Identified", count: identified, color: "text-gray-600 bg-gray-50 border-gray-200" },
        ].map(s => (
          <div key={s.label} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium ${s.color}`}>
            <span className="text-base font-bold">{s.count}</span>
            {s.label}
          </div>
        ))}
      </div>

      {/* Synergy cards */}
      <div className="space-y-3">
        {synergies.map(syn => {
          const Icon = SYNERGY_ICONS[syn.category]
          const colors = SYNERGY_COLORS[syn.category]
          const isOpen = expanded === syn.id
          return (
            <div
              key={syn.id}
              className={`rounded-xl border ${colors.border} bg-white overflow-hidden`}
            >
              <button
                className="w-full flex items-center gap-3 p-4 text-left hover:bg-gray-50 transition-colors"
                onClick={() => setExpanded(isOpen ? null : syn.id)}
              >
                <div className={`p-1.5 rounded-lg ${colors.bg}`}>
                  <Icon className={`h-3.5 w-3.5 ${colors.icon}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-gray-900">{syn.title}</span>
                    <span className={`text-[10px] font-semibold rounded-full px-2 py-0.5 uppercase tracking-wide ${SYNERGY_STATUS_BADGE[syn.status]}`}>
                      {syn.status.replace("_", " ")}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 truncate mt-0.5">{syn.description}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className={`text-xs font-semibold ${colors.text} hidden sm:block`}>{syn.potentialValue}</span>
                  {isOpen ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
                </div>
              </button>

              {isOpen && (
                <div className={`px-4 pb-4 pt-0 ${colors.bg} border-t ${colors.border}`}>
                  <p className="text-sm text-gray-700 leading-relaxed mt-3">{syn.description}</p>
                  <div className="flex items-center gap-2 mt-3">
                    <TrendingUp className={`h-3.5 w-3.5 ${colors.icon}`} />
                    <span className={`text-xs font-semibold ${colors.text}`}>{syn.potentialValue}</span>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button className="text-xs px-3 py-1.5 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                      Discuss in Chat
                    </button>
                    {syn.status !== "agreed" && (
                      <button className="text-xs px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
                        Mark as Agreed
                      </button>
                    )}
                    {syn.status === "agreed" && (
                      <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Agreed
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Investor interest banner ───────────────────────────────────────────────

function InvestorInterestBanner({ room }: { room: DealRoom }) {
  const investors = room.members.filter(m => m.role !== "admin" || m.org_name !== room.members[0]?.org_name)
  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 flex items-center gap-3">
      <Building2 className="h-4 w-4 text-blue-500 shrink-0" />
      <p className="text-xs text-blue-700">
        <span className="font-semibold">{investors.length} investor{investors.length !== 1 ? "s" : ""}</span> in this room
        {room.members.filter(m => m.nda_signed_at).length > 0 && (
          <> · <span className="font-semibold">{room.members.filter(m => m.nda_signed_at).length}</span> NDA{room.members.filter(m => m.nda_signed_at).length !== 1 ? "s" : ""} signed</>
        )}
        <span className="text-blue-500"> · Respond within 24h to maintain engagement</span>
      </p>
      <Clock className="h-3.5 w-3.5 text-blue-400 ml-auto shrink-0" />
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function DealRoomsPage() {
  const { mode } = usePlatformModeStore()
  const isAlly = mode === "ally"

  const [selectedRoom, setSelectedRoom] = useState<string | null>(
    isAlly ? "ally-room-1" : "room-p2"
  )
  const [showCreate, setShowCreate] = useState(false)
  const [showInvite, setShowInvite] = useState(false)
  const [newMessage, setNewMessage] = useState("")
  const [newRoom, setNewRoom] = useState({ name: "", project_id: "", nda_required: true, download_restricted: false })
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("viewer")
  const [detailTab, setDetailTab] = useState<"messages" | "qa" | "synergies">("messages")
  const [showAskForm, setShowAskForm] = useState(false)
  const [qaForm, setQaForm] = useState({ category: "financial", priority: "normal", title: "", body: "" })

  const { data: apiRooms = [] } = useDealRooms()

  // Choose mock data based on mode
  const mockRooms   = isAlly ? MOCK_ALLY_ROOMS   : MOCK_ROOMS
  const mockMessages = isAlly ? MOCK_ALLY_MESSAGES : MOCK_MESSAGES
  const mockActivities = isAlly ? MOCK_ALLY_ACTIVITIES : MOCK_ACTIVITIES
  const nameMap = isAlly ? INVESTOR_NAMES : DEAL_NAMES

  const rooms: DealRoom[] = apiRooms.length > 0 ? apiRooms : mockRooms
  const { data: apiMessages = [], refetch: refetchMessages } = useRoomMessages(selectedRoom)
  const messages: DealRoomMessage[] = apiMessages.length > 0 ? apiMessages : (selectedRoom ? (mockMessages[selectedRoom] ?? []) : [])
  const { data: apiActivities = [] } = useRoomActivity(selectedRoom)
  const activities: DealRoomActivity[] = apiActivities.length > 0 ? apiActivities : (selectedRoom ? (mockActivities[selectedRoom] ?? []) : [])
  const createMutation = useCreateRoom()
  const inviteMutation = useInviteMember(selectedRoom ?? "")
  const messageMutation = useSendMessage(selectedRoom ?? "")

  const activeRoom = rooms.find(r => r.id === selectedRoom)
  const projectId = activeRoom?.project_id ? String(activeRoom.project_id) : undefined
  const { data: questions = [] } = useProjectQuestions(projectId)
  const { data: qaStats } = useQAStats(projectId)
  const createQuestion = useCreateQuestion()

  // Reset detail tab when switching rooms
  const handleSelectRoom = (id: string) => {
    setSelectedRoom(id)
    setDetailTab("messages")
  }

  const tabs = isAlly
    ? (["messages", "synergies", "qa"] as const)
    : (["messages", "qa"] as const)

  const tabLabels: Record<string, { icon: React.ComponentType<{className?: string}>, label: string }> = {
    messages:  { icon: MessageSquare, label: "Messages" },
    synergies: { icon: Handshake,     label: "Synergies" },
    qa:        { icon: HelpCircle,    label: "Q&A" },
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {isAlly ? "Deal Room" : "Deal Rooms"}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {isAlly
              ? "Communicate with interested investors and discuss deals, terms, and synergies"
              : "Secure spaces for multi-party deal collaboration"}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" />
          New Room
        </button>
      </div>

      {/* Ally-side summary bar */}
      {isAlly && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Active Conversations", value: rooms.filter(r => r.status === "active").length, icon: MessageSquare, color: "text-blue-600 bg-blue-50" },
            { label: "Investors Engaged", value: rooms.reduce((acc, r) => acc + r.members.filter(m => m.joined_at).length, 0), icon: Users, color: "text-green-600 bg-green-50" },
            { label: "Synergies Identified", value: Object.values(MOCK_SYNERGIES).flat().length, icon: Handshake, color: "text-purple-600 bg-purple-50" },
          ].map(stat => {
            const Icon = stat.icon
            return (
              <div key={stat.label} className="rounded-xl border border-gray-200 bg-white px-4 py-3 flex items-center gap-3">
                <div className={`p-2 rounded-lg ${stat.color}`}>
                  <Icon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-xl font-bold text-gray-900">{stat.value}</p>
                  <p className="text-xs text-gray-500">{stat.label}</p>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="flex gap-6">
        {/* Room list */}
        <div className="w-72 flex-shrink-0 space-y-2">
          {rooms.map((room) => (
            <button
              key={room.id}
              onClick={() => handleSelectRoom(room.id)}
              className={`w-full text-left rounded-xl border p-4 transition-colors ${selectedRoom === room.id ? "border-primary-300 bg-primary-50" : "border-gray-200 bg-white hover:bg-gray-50"}`}
            >
              <div className="flex items-start justify-between">
                <p className="font-semibold text-gray-900 text-sm truncate pr-2">{room.name}</p>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${STATUS_BADGE[room.status] ?? "bg-gray-100 text-gray-600"}`}>
                  {room.status}
                </span>
              </div>
              {isAlly ? (
                <p className="text-xs text-gray-500 mt-1 truncate">
                  {room.members.filter(m => m.joined_at).length} investor{room.members.filter(m => m.joined_at).length !== 1 ? "s" : ""} active
                </p>
              ) : (
                <p className="text-xs text-gray-500 mt-1 truncate font-mono">{String(room.project_id).slice(0, 8)}…</p>
              )}
              <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                <span className="flex items-center gap-1"><Users className="h-3.5 w-3.5" />{room.members.length}</span>
                {room.settings.nda_required && <Lock className="h-3.5 w-3.5 text-orange-500" />}
                {isAlly && MOCK_SYNERGIES[room.id]?.length > 0 && (
                  <span className="flex items-center gap-1 ml-auto text-purple-500">
                    <Handshake className="h-3.5 w-3.5" />
                    {MOCK_SYNERGIES[room.id].length}
                  </span>
                )}
              </div>
            </button>
          ))}
          {rooms.length === 0 && (
            <div className="text-center py-8 border border-dashed border-gray-300 rounded-xl text-gray-500">
              <Users className="h-8 w-8 text-gray-300 mx-auto mb-2" />
              <p className="text-sm">No deal rooms yet</p>
            </div>
          )}
        </div>

        {/* Room detail */}
        {selectedRoom && activeRoom ? (
          <div className="flex-1 min-w-0 space-y-4">
            {/* Room header */}
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">{activeRoom.name}</h2>
                  <p className="text-sm text-gray-500 font-mono">{String(activeRoom.project_id).slice(0, 8)}…</p>
                </div>
                <div className="flex items-center gap-2">
                  {activeRoom.settings.nda_required && (
                    <span className="flex items-center gap-1 text-xs text-orange-600 bg-orange-50 border border-orange-200 rounded-lg px-2 py-1">
                      <Lock className="h-3.5 w-3.5" /> NDA Required
                    </span>
                  )}
                  {activeRoom.settings.download_restricted && (
                    <span className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 border border-blue-200 rounded-lg px-2 py-1">
                      <Eye className="h-3.5 w-3.5" /> View-only
                    </span>
                  )}
                  <button
                    onClick={() => setShowInvite(true)}
                    className="flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
                  >
                    <Plus className="h-4 w-4" /> Invite
                  </button>
                </div>
              </div>

              {/* Member chips */}
              <div className="flex flex-wrap gap-2 mt-3">
                {activeRoom.members.map(m => (
                  <div key={m.id} className="flex items-center gap-1.5 text-xs bg-gray-100 rounded-full px-2.5 py-1 text-gray-600">
                    <div className="h-4 w-4 rounded-full bg-primary-200 flex items-center justify-center text-[9px] font-bold text-primary-700">
                      {(m.org_name ?? m.email ?? "?")[0]?.toUpperCase()}
                    </div>
                    <span className="font-medium truncate max-w-[120px]">{m.org_name ?? m.email}</span>
                    {m.nda_signed_at && <Lock className="h-3 w-3 text-orange-400" />}
                  </div>
                ))}
              </div>
            </div>

            {/* Ally interest banner */}
            {isAlly && <InvestorInterestBanner room={activeRoom} />}

            {/* Detail tabs */}
            <div className="flex gap-1 border-b border-gray-200">
              {tabs.map((tab) => {
                const { icon: TabIcon, label } = tabLabels[tab]
                return (
                  <button
                    key={tab}
                    onClick={() => setDetailTab(tab)}
                    className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${detailTab === tab ? "border-primary-600 text-primary-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}
                  >
                    <TabIcon className="h-3.5 w-3.5" />
                    {label}
                    {tab === "qa" && qaStats && qaStats.open > 0 && (
                      <span className="ml-1 rounded-full bg-primary-100 px-1.5 py-0.5 text-[10px] font-semibold text-primary-700">{qaStats.open}</span>
                    )}
                    {tab === "synergies" && MOCK_SYNERGIES[selectedRoom]?.length > 0 && (
                      <span className="ml-1 rounded-full bg-purple-100 px-1.5 py-0.5 text-[10px] font-semibold text-purple-700">
                        {MOCK_SYNERGIES[selectedRoom].length}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>

            {/* Synergies tab */}
            {detailTab === "synergies" && isAlly && (
              <SynergiesTab roomId={selectedRoom} />
            )}

            {/* Q&A tab */}
            {detailTab === "qa" && (
              <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
                {qaStats && (
                  <div className="flex gap-4 text-xs text-gray-500">
                    <span>Open: <strong className="text-gray-700">{qaStats.open}</strong></span>
                    <span>Answered: <strong className="text-gray-700">{qaStats.answered}</strong></span>
                    {qaStats.sla_breached > 0 && (
                      <span className="text-red-600">SLA Breached: <strong>{qaStats.sla_breached}</strong></span>
                    )}
                  </div>
                )}
                {showAskForm ? (
                  <div className="rounded-lg border border-gray-200 p-4 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
                        <select className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" value={qaForm.category} onChange={e => setQaForm(f => ({ ...f, category: e.target.value }))}>
                          {["financial","legal","technical","commercial","regulatory","esg","operational"].map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Priority</label>
                        <select className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" value={qaForm.priority} onChange={e => setQaForm(f => ({ ...f, priority: e.target.value }))}>
                          {["urgent","high","normal","low"].map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                      </div>
                    </div>
                    <input className="w-full border border-gray-300 rounded px-3 py-2 text-sm" placeholder="Question title" value={qaForm.title} onChange={e => setQaForm(f => ({ ...f, title: e.target.value }))} />
                    <textarea className="w-full border border-gray-300 rounded px-3 py-2 text-sm resize-none" rows={3} placeholder="Question body" value={qaForm.body} onChange={e => setQaForm(f => ({ ...f, body: e.target.value }))} />
                    <div className="flex gap-2">
                      <button className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50" disabled={!qaForm.title.trim() || createQuestion.isPending} onClick={() => {
                        if (!projectId) return
                        createQuestion.mutate({ project_id: projectId, ...qaForm }, { onSuccess: () => { setShowAskForm(false); setQaForm({ category: "financial", priority: "normal", title: "", body: "" }) } })
                      }}>Submit</button>
                      <button className="px-3 py-1.5 border border-gray-300 rounded text-sm" onClick={() => setShowAskForm(false)}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <button className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50" onClick={() => setShowAskForm(true)}>
                    <Plus className="h-4 w-4" /> Ask Question
                  </button>
                )}
                {questions.length === 0 ? (
                  <p className="text-center text-sm text-gray-400 py-8">No questions yet.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead><tr className="border-b text-left text-gray-500">
                        <th className="py-2 pr-3 font-medium">#</th>
                        <th className="py-2 pr-3 font-medium">Category</th>
                        <th className="py-2 pr-3 font-medium">Priority</th>
                        <th className="py-2 pr-3 font-medium">Status</th>
                        <th className="py-2 font-medium">Title</th>
                      </tr></thead>
                      <tbody>
                        {questions.map(q => (
                          <tr key={q.id} className="border-b last:border-0">
                            <td className="py-2 pr-3 text-gray-400">{q.question_number}</td>
                            <td className="py-2 pr-3 capitalize text-gray-700">{q.category}</td>
                            <td className="py-2 pr-3">
                              <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${q.priority === "urgent" ? "bg-red-100 text-red-700" : q.priority === "high" ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600"}`}>{q.priority}</span>
                            </td>
                            <td className="py-2 pr-3">
                              <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${q.status === "answered" ? "bg-green-100 text-green-700" : q.sla_breached ? "bg-red-100 text-red-700" : "bg-blue-100 text-blue-700"}`}>{q.sla_breached ? "SLA breach" : q.status}</span>
                            </td>
                            <td className="py-2 text-gray-900">{q.title}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Messages tab */}
            {detailTab === "messages" && (
              <div className="grid grid-cols-3 gap-4">
                {/* Message thread */}
                <div className="col-span-2 rounded-xl border border-gray-200 bg-white flex flex-col" style={{ height: 480 }}>
                  <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100">
                    <MessageSquare className="h-4 w-4 text-gray-400" />
                    <span className="font-semibold text-gray-900 text-sm">Messages</span>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {messages.map((msg) => {
                      const displayName = nameMap[msg.user_id] ?? msg.user_id.slice(0, 8) + "…"
                      const initials = displayName.split(" ").slice(0, 2).map((w: string) => w[0] ?? "").join("").toUpperCase()
                      return (
                        <div key={msg.id} className="flex gap-3">
                          <div className="h-7 w-7 rounded-full bg-primary-100 flex items-center justify-center text-xs font-bold text-primary-700 flex-shrink-0">
                            {initials}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-baseline gap-2">
                              <span className="text-sm font-medium text-gray-900">{displayName}</span>
                              <span className="text-xs text-gray-400">{formatDate(msg.created_at)}</span>
                            </div>
                            <p className="text-sm text-gray-700 mt-0.5">{msg.content}</p>
                          </div>
                        </div>
                      )
                    })}
                    {messages.length === 0 && (
                      <p className="text-center text-sm text-gray-400 py-8">No messages yet. Start the conversation.</p>
                    )}
                  </div>
                  <div className="p-3 border-t border-gray-100">
                    <div className="flex gap-2">
                      <textarea
                        rows={2}
                        className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
                        placeholder={isAlly ? "Reply to investor… (Enter to send)" : "Type a message… (Enter to send)"}
                        value={newMessage}
                        onChange={e => setNewMessage(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault()
                            if (newMessage.trim()) messageMutation.mutate(newMessage.trim(), { onSuccess: () => { refetchMessages(); setNewMessage("") } })
                          }
                        }}
                      />
                      <button
                        onClick={() => { if (newMessage.trim()) messageMutation.mutate(newMessage.trim(), { onSuccess: () => { refetchMessages(); setNewMessage("") } }) }}
                        disabled={!newMessage.trim() || messageMutation.isPending}
                        className="flex-shrink-0 flex items-center justify-center h-10 w-10 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                      >
                        <Send className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Activity feed */}
                <div className="rounded-xl border border-gray-200 bg-white flex flex-col" style={{ height: 480 }}>
                  <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100">
                    <Activity className="h-4 w-4 text-gray-400" />
                    <span className="font-semibold text-gray-900 text-sm">Activity</span>
                  </div>
                  <div className="flex-1 overflow-y-auto p-3 space-y-3">
                    {activities.map((act) => {
                      const shortNames: Record<string, string> = isAlly ? {
                        "user-nordic-cap": "Nordic Cap", "user-ally-porto": "Porto Solar",
                        "user-iberian":    "Iberian GV", "user-euro-infra":  "EuroInfra",
                        "user-aegean":     "Aegean Wind","user-hellas-pe":   "Hellas PE",
                        "user-alpine":     "Alpine Hydro","user-swiss-re":   "Swiss Re",
                        "user-zurich-pen": "Zürich Pen",
                      } : {
                        "user-sofia": "Sofia B.", "user-erik": "Erik L.",
                        "user-marco": "Marco R.", "user-danube": "Danube Hydro",
                        "user-aegean": "Aegean Wind", "user-bavarian": "Bavarian Biomass",
                      }
                      const displayName = shortNames[act.user_id] ?? act.user_id.slice(0, 8) + "…"
                      return (
                        <div key={act.id} className="flex gap-2 text-xs">
                          <div className="h-5 w-5 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <Activity className="h-3 w-3 text-gray-400" />
                          </div>
                          <div>
                            <span className="font-medium text-gray-700">{displayName}</span>
                            {act.description
                              ? <span className="text-gray-500"> {act.description}</span>
                              : <span className="text-gray-500"> {act.activity_type.replace(/_/g, " ")}</span>
                            }
                            <p className="text-gray-400 mt-0.5">{formatDate(act.created_at)}</p>
                          </div>
                        </div>
                      )
                    })}
                    {activities.length === 0 && (
                      <p className="text-center text-xs text-gray-400 py-8">No activity yet</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <Users className="h-12 w-12 text-gray-200 mx-auto mb-3" />
              <p className="font-medium text-gray-500">Select a deal room</p>
              <p className="text-sm mt-1">or create a new one to get started</p>
            </div>
          </div>
        )}
      </div>

      {/* Create Room Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Create Deal Room</h2>
              <button onClick={() => setShowCreate(false)}><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Room Name *</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="e.g. Solar Farm A — Series A"
                value={newRoom.name}
                onChange={e => setNewRoom(d => ({ ...d, name: e.target.value }))} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Project ID</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="UUID of the project"
                value={newRoom.project_id}
                onChange={e => setNewRoom(d => ({ ...d, project_id: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" className="rounded"
                  checked={newRoom.nda_required}
                  onChange={e => setNewRoom(d => ({ ...d, nda_required: e.target.checked }))} />
                <Lock className="h-4 w-4 text-orange-500" />
                Require NDA before access
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" className="rounded"
                  checked={newRoom.download_restricted}
                  onChange={e => setNewRoom(d => ({ ...d, download_restricted: e.target.checked }))} />
                <Eye className="h-4 w-4 text-blue-500" />
                Restrict downloads (view-only)
              </label>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button
                onClick={() => createMutation.mutate({ name: newRoom.name, project_id: newRoom.project_id, settings: { nda_required: newRoom.nda_required, download_restricted: newRoom.download_restricted } }, { onSuccess: (data) => { setShowCreate(false); setSelectedRoom(data.id) } })}
                disabled={!newRoom.name || createMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {createMutation.isPending ? "Creating…" : "Create Room"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Invite Modal */}
      {showInvite && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">
                {isAlly ? "Invite Investor" : "Invite Member"}
              </h2>
              <button onClick={() => setShowInvite(false)}><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
              <input type="email" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder={isAlly ? "investor@fund.com" : "colleague@firm.com"}
                value={inviteEmail}
                onChange={e => setInviteEmail(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={inviteRole} onChange={e => setInviteRole(e.target.value)}>
                {["viewer", "member", "admin"].map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowInvite(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button
                onClick={() => inviteMutation.mutate({ email: inviteEmail, role: inviteRole }, { onSuccess: () => { setShowInvite(false); setInviteEmail("") } })}
                disabled={!inviteEmail || inviteMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {inviteMutation.isPending ? "Inviting…" : "Send Invite"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
