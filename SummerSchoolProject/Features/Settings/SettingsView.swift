//
//  SettingsView.swift
//  SummerSchoolProject
//

import Combine
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var outbox: OutboxStore
    @EnvironmentObject private var processor: OutboxProcessor
    @EnvironmentObject private var monitor: NetworkMonitor

    private let demoUsers = ["Пользователь A", "Пользователь B"]

    var body: some View {
        NavigationStack {
            List {
                Section("Состояние сети") {
                    HStack {
                        Image(systemName: monitor.isOnline ? "wifi" : "wifi.slash")
                            .foregroundStyle(monitor.isOnline ? Color.green : Color.red)
                        Text(monitor.isOnline ? "Онлайн" : "Офлайн (Airplane Mode?)")
                            .foregroundStyle(monitor.isOnline ? Color.primary : Color.red)
                        Spacer()
                        Circle()
                            .fill(monitor.isOnline ? Color.green : Color.red)
                            .frame(width: 8, height: 8)
                    }
                }

                Section {
                    OutboxStatusSection()
                } header: {
                    Text("Очередь отложенных действий")
                } footer: {
                    Text("Действия, совершённые офлайн, хранятся здесь и отправляются автоматически при появлении сети.")
                        .font(.caption)
                }

                Section("Текущая сессия") {
                    if let user = session.currentUser {
                        LabeledContent("Вошёл как", value: user)
                        Button(role: .destructive) {
                            session.logout()
                        } label: {
                            Label("Выйти (+ очистить кэш, очередь, Keychain)", systemImage: "door.left.hand.open")
                        }
                    } else {
                        Text("Не авторизован").foregroundStyle(.secondary)
                    }
                }

                Section("Войти как…") {
                    ForEach(demoUsers, id: \.self) { name in
                        Button { session.login(as: name) } label: {
                            Label(name, systemImage: "person.circle")
                        }
                        .disabled(session.currentUser == name)
                    }
                }

                Section {
                    KeychainTokenSection()
                } header: {
                    Text("🔒 Безопасность · Keychain")
                } footer: {
                    Text("Токен хранится с классом kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly: доступен в фоне после первой разблокировки, но не уезжает в iCloud-бэкап на другое устройство.")
                        .font(.caption)
                }

                Section {
                    UserDefaultsAntipatternSection()
                } header: {
                    Text("⚠️ Антипример · UserDefaults (plain plist)")
                } footer: {
                    Text("ТОЛЬКО ДЛЯ ДЕМО. В продакшне токен нельзя хранить в UserDefaults — это plain-text plist без шифрования.")
                        .font(.caption)
                        .foregroundStyle(.orange)
                }

                Section {
                    CacheInfoRow()
                } header: {
                    Text("Состояние кэша")
                } footer: {
                    Text("TTL: \(Int(CacheManager.cacheTTL)) сек · Версия схемы: \(CacheManager.cacheSchemaVersion)")
                        .font(.caption)
                }

                Section {
                    Button(role: .destructive) {
                        CacheManager.shared.clearAll()
                    } label: {
                        Label("Очистить весь кэш вручную", systemImage: "trash")
                    }
                } footer: {
                    Text("При выходе из аккаунта clearAll() вызывается автоматически.")
                        .font(.caption)
                }
            }
            .navigationTitle("Настройки")
        }
    }
}

// MARK: - KeychainTokenSection

private struct KeychainTokenSection: View {
    @EnvironmentObject private var session: SessionStore

    var body: some View {
        if let token = session.accessToken {
            LabeledContent("Токен (Keychain)") {
                Text(String(token.prefix(20)) + "…")
                    .font(.caption).monospaced().foregroundStyle(.green)
            }
            LabeledContent("Хранилище") {
                Text("Keychain · AES-256")
                    .font(.caption).foregroundStyle(.green)
            }
            LabeledContent("Класс доступности") {
                Text("AfterFirstUnlockThisDeviceOnly")
                    .font(.caption2).monospaced().foregroundStyle(.secondary)
            }
            LabeledContent("Authorization-заголовок") {
                Text("Bearer \(String(token.prefix(12)))…")
                    .font(.caption2).monospaced().foregroundStyle(.secondary)
            }
        } else {
            Label("Токен отсутствует — войдите в аккаунт", systemImage: "lock.slash")
                .foregroundStyle(.secondary).font(.subheadline)
        }
    }
}

// MARK: - UserDefaultsAntipatternSection

private struct UserDefaultsAntipatternSection: View {
    private let demoUDKey = "DEMO_ONLY.insecureToken"
    @State private var isExpanded = false

    var body: some View {
        Button {
            let fakeToken = "INSECURE-\(UUID().uuidString.prefix(8))"
            UserDefaults.standard.set(fakeToken, forKey: demoUDKey)
            isExpanded = true
        } label: {
            Label("Записать токен в UserDefaults (антипример)", systemImage: "exclamationmark.triangle")
                .foregroundStyle(.orange)
        }

        if isExpanded {
            let udToken = UserDefaults.standard.string(forKey: demoUDKey)

            LabeledContent("Читается из UserDefaults") {
                Text(udToken ?? "—")
                    .font(.caption).monospaced()
                    .foregroundStyle(.red)
            }

            LabeledContent("Путь к plain-text plist") {
                Text(plistFilePath())
                    .font(.caption2).foregroundStyle(.orange)
                    .lineLimit(3).multilineTextAlignment(.trailing)
            }

            Text("☝️ Открой этот файл — токен виден как plain text!\nВ Keychain тот же токен зашифрован AES-256.")
                .font(.caption).foregroundStyle(.orange).padding(.vertical, 2)

            Button(role: .destructive) {
                UserDefaults.standard.removeObject(forKey: demoUDKey)
                isExpanded = false
            } label: {
                Label("Удалить антипример из UserDefaults", systemImage: "trash")
            }
            .font(.caption)
        }
    }

    private func plistFilePath() -> String {
        let bundle = Bundle.main.bundleIdentifier ?? "app"
        let libraryDir = FileManager.default.urls(for: .libraryDirectory, in: .userDomainMask).first
        let filePath = libraryDir?.appendingPathComponent("Preferences/\(bundle).plist").path
            ?? "Library/Preferences/\(bundle).plist"
        print(filePath)
        return filePath
    }
}

// MARK: - OutboxStatusSection

private struct OutboxStatusSection: View {
    @EnvironmentObject private var outbox: OutboxStore
    @EnvironmentObject private var processor: OutboxProcessor
    @EnvironmentObject private var monitor: NetworkMonitor

    var body: some View {
        HStack {
            Image(systemName: "tray.and.arrow.up")
                .foregroundStyle(outbox.pendingCount > 0 ? Color.orange : Color.secondary)
            Text("Ожидают отправки")
            Spacer()
            Text("\(outbox.pendingCount)")
                .foregroundStyle(outbox.pendingCount > 0 ? Color.orange : Color.secondary)
                .monospacedDigit()
        }

        let failedCount = outbox.items.filter { $0.status == .failed }.count
        if failedCount > 0 {
            HStack {
                Image(systemName: "exclamationmark.triangle").foregroundStyle(.red)
                Text("Не удалось отправить")
                Spacer()
                Text("\(failedCount)").foregroundStyle(.red).monospacedDigit()
            }
        }

        Button {
            Task { await processor.processQueue() }
        } label: {
            Label("Синхронизировать сейчас", systemImage: "arrow.triangle.2.circlepath")
        }
        .disabled(!monitor.isOnline || outbox.pendingCount == 0)

        if outbox.items.isEmpty {
            Text("Очередь пуста — всё синхронизировано ✓")
                .font(.subheadline).foregroundStyle(.secondary)
        } else {
            ForEach(outbox.items.prefix(5)) { item in OutboxItemRow(item: item) }
            if outbox.items.count > 5 {
                Text("… и ещё \(outbox.items.count - 5) элементов")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
    }
}

// MARK: - OutboxItemRow

private struct OutboxItemRow: View {
    let item: OutboxItem

    var body: some View {
        HStack(spacing: 8) {
            statusIcon
            VStack(alignment: .leading, spacing: 2) {
                Text(actionTitle).font(.subheadline)
                Text("ID: \(item.clientID.uuidString.prefix(8))… · попыток: \(item.retryCount)")
                    .font(.caption2).foregroundStyle(.secondary).monospaced()
            }
            Spacer()
        }
    }

    private var statusIcon: some View {
        Group {
            switch item.status {
            case .pending:  Image(systemName: "clock").foregroundStyle(.orange)
            case .inFlight: Image(systemName: "paperplane").foregroundStyle(.blue)
            case .failed:   Image(systemName: "xmark.circle").foregroundStyle(.red)
            }
        }
        .font(.subheadline)
    }

    private var actionTitle: String {
        switch item.action { case .likePost(let id): return "Лайк поста #\(id)" }
    }
}

// MARK: - CacheInfoRow

private struct CacheInfoRow: View {
    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()
    @State private var now = Date()

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            infoLine("URLCache (диск)", "\(CacheManager.shared.urlCache.currentDiskUsage / 1024) KB")
            infoLine("URLCache (RAM)", "\(CacheManager.shared.urlCache.currentMemoryUsage / 1024) KB")
            infoLine("Возраст /posts", ageString(for: "endpoint.posts"))
            infoLine("Возраст /users/1", ageString(for: "endpoint.user.1"))
        }
        .font(.caption)
        .onReceive(timer) { now = $0 }
    }

    private func infoLine(_ label: String, _ value: String) -> some View {
        HStack { Text(label).foregroundStyle(.secondary); Spacer(); Text(value) }
    }

    private func ageString(for key: String) -> String {
        guard
            let data = UserDefaults.standard.data(forKey: "cache.timestamps.v1"),
            let dict = try? JSONDecoder().decode([String: Date].self, from: data),
            let savedAt = dict[key]
        else { return "нет данных" }

        let age = now.timeIntervalSince(savedAt)
        let ttl = CacheManager.cacheTTL
        if age <= ttl { return String(format: "%.0f с (свежий, TTL %.0f с)", age, ttl) }
        return String(format: "%.0f с (⚠️ устарел, TTL %.0f с)", age, ttl)
    }
}
