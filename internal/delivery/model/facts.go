package model

const FactPrefix = "fact://"
const ContextFact = FactPrefix + "context"
const FileIdentityFactPrefix = FactPrefix + "file-identity/"

// Fact 读取快照已冻结的逻辑事实；与同名项目文件保持不同命名域。
func Fact(s Snapshot, name string) ([]byte, bool) { return s.Document(FactPrefix + name) }
