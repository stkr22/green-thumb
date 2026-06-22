{{/*
Base name, overridable via nameOverride.
*/}}
{{- define "green-thumb.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Fully qualified app name. Component templates suffix this (e.g. "-backend").
Honors fullnameOverride; otherwise derives from the release name, collapsing the
common case where the release is named after the chart (green-thumb-green-thumb).
*/}}
{{- define "green-thumb.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "green-thumb.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels applied to every object.
*/}}
{{- define "green-thumb.labels" -}}
helm.sh/chart: {{ include "green-thumb.chart" . }}
app.kubernetes.io/name: {{ include "green-thumb.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Backend selector/workload names. The `app:` selector label is kept for parity
with the pre-chart manifests so existing NetworkPolicies/dashboards still match.
*/}}
{{- define "green-thumb.backend.fullname" -}}
{{- printf "%s-backend" (include "green-thumb.fullname" .) -}}
{{- end -}}

{{- define "green-thumb.backend.selectorLabels" -}}
app: {{ include "green-thumb.backend.fullname" . }}
app.kubernetes.io/name: {{ include "green-thumb.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: backend
{{- end -}}

{{/*
PVC name: the existing claim if provided, otherwise the chart-managed one.
*/}}
{{- define "green-thumb.pvcName" -}}
{{- if .Values.persistence.existingClaim -}}
{{- .Values.persistence.existingClaim -}}
{{- else -}}
{{- printf "%s-data" (include "green-thumb.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/*
Resolve an image tag, defaulting to the chart appVersion.
Usage: include "green-thumb.image" (dict "image" .Values.backend.image "root" .)
*/}}
{{- define "green-thumb.image" -}}
{{- $tag := .image.tag | default .root.Chart.AppVersion -}}
{{- printf "%s:%s" .image.repository $tag -}}
{{- end -}}
