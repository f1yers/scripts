{{- define "command.java" -}}
["sh", "-c", "exec java -javaagent:/var/telemetry/otel.jar -Djava.security.egd=file:/dev/./urandom -Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.port=1099 -Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false{{ if .Values.javaOpts }} {{ .Values.javaOpts }}{{ end }} -jar app.jar"]
{{- end }}
