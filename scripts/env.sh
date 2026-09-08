# Source this before running Maven/Spring Boot commands:
#   source scripts/env.sh
#
# openjdk is keg-only on Homebrew (macOS ships its own /usr/bin/java stub
# that just errors), so it isn't on PATH by default. maven and prometheus
# are already symlinked into /opt/homebrew/bin and need no extra PATH entry
# — this is here mainly for java, plus JAVA_HOME for Maven's benefit.

export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
export JAVA_HOME="/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home"
