#!/bin/sh
# Report observable question channels; client-provided tools are not observable here.
json_string() {
    if [ -z "$1" ]; then
        printf 'null'
        return
    fi
    printf '%sx\n' "$1" | awk '
        NR > 1 { value = value "\n" }
        { value = value $0 }
        END {
            value = substr(value, 1, length(value) - 1)
            printf "\""
            for (i = 1; i <= length(value); i++) {
                c = substr(value, i, 1)
                if (c == "\"") printf "\\\""
                else if (c == "\\") printf "\\\\"
                else {
                    control = 0
                    for (j = 1; j < 32; j++)
                        if (c == sprintf("%c", j)) { control = j; break }
                    if (control) printf "\\u%04x", control
                    else printf "%s", c
                }
            }
            printf "\""
        }'
}

agtermctl=$(command -v agtermctl 2>/dev/null || :)
picker=unavailable
if [ "${AGTERM_ENABLED:-}" = 1 ] && [ -n "$agtermctl" ] &&
   [ -n "${AGTERM_SESSION_ID:-}" ] && [ -n "${AGTERM_WINDOW_ID:-}" ]; then
    picker=candidate
fi

printf '{"environment":{"AGTERM_ENABLED":'
json_string "${AGTERM_ENABLED:-}"
printf ',"AGTERM_SESSION_ID":'
json_string "${AGTERM_SESSION_ID:-}"
printf ',"AGTERM_WINDOW_ID":'
json_string "${AGTERM_WINDOW_ID:-}"
printf ',"AGTERM_SOCKET":'
json_string "${AGTERM_SOCKET:-}"
printf '},"agtermctl":'
json_string "$agtermctl"
printf ',"agterm_picker":"%s","client_question_tools":"unknown: inspect tools exposed by the current client and mode"}\n' "$picker"
