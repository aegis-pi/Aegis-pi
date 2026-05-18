{{- define "aegis-spoke.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "aegis-spoke.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := include "aegis-spoke.name" . -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "aegis-spoke.namespace" -}}
{{- default .Release.Namespace .Values.namespaceOverride -}}
{{- end -}}

{{- define "aegis-spoke.labels" -}}
app.kubernetes.io/name: {{ include "aegis-spoke.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: aegis-spoke
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
aegis.factory/id: {{ .Values.factory.id | quote }}
{{- end -}}

{{- define "aegis-spoke.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (printf "%s-data-plane" (include "aegis-spoke.fullname" .)) .Values.serviceAccount.name -}}
{{- else -}}
{{- .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
