# выбранные задачи:

**basic**:
1. deliver.tla (spec_id: 22)
MissionariesAndCannibalsTyped.tla (spec_id: 166)
**intermediate:**
1. TrafficLight.tla (spec_id: 27)
2. PrisonersTyped.tla (spec_id: 195)


tla2lools:

скачать:

Invoke-WebRequest -Uri "https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar" -OutFile ".\tla2tools.jar"

java -cp tla2tools.jar tla2sany.SANY Spec.tla
java -cp tla2tools.jar tlc2.TLC -config Spec.cfg -workers auto Spec.tla