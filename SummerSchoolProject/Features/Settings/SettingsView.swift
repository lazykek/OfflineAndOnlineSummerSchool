//
//  SettingsView.swift
//  SummerSchoolProject
//

import Combine
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var session: SessionStore

    private let demoUsers = ["Пользователь A", "Пользователь B"]

    var body: some View {
        NavigationStack {
            List {
                Section("Текущая сессия") {
                    if let user = session.currentUser {
                        LabeledContent("Вошёл как", value: user)
                        Button(role: .destructive) {
                            session.logout()
                        } label: {
                            Label("Выйти (+ очистить кэш)", systemImage: "door.left.hand.open")
                        }
                    } else {
                        Text("Не авторизован")
                            .foregroundStyle(.secondary)
                    }
                }

                Section("Войти как…") {
                    ForEach(demoUsers, id: \.self) { name in
                        Button {
                            session.login(as: name)
                        } label: {
                            Label(name, systemImage: "person.circle")
                        }
                        .disabled(session.currentUser == name)
                    }
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
                    Text("При выходе из аккаунта clearAll() вызывается автоматически, чтобы данные одного пользователя не утекли к другому.")
                        .font(.caption)
                }
            }
            .navigationTitle("Настройки")
        }
    }
}

// MARK: - Cache info row

private struct CacheInfoRow: View {
    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()
    @State private var now = Date()

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            infoLine("URLCache (диск)",
                     "\(CacheManager.shared.urlCache.currentDiskUsage / 1024) KB")
            infoLine("URLCache (RAM)",
                     "\(CacheManager.shared.urlCache.currentMemoryUsage / 1024) KB")
            infoLine("Возраст /posts", ageString(for: "endpoint.posts"))
            infoLine("Возраст /users/1", ageString(for: "endpoint.user.1"))
        }
        .font(.caption)
        .onReceive(timer) { now = $0 }
    }

    private func infoLine(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            Text(value)
        }
    }

    private func ageString(for key: String) -> String {
        guard
            let data = UserDefaults.standard.data(forKey: "cache.timestamps.v1"),
            let dict = try? JSONDecoder().decode([String: Date].self, from: data),
            let savedAt = dict[key]
        else { return "нет данных" }

        let age = now.timeIntervalSince(savedAt)
        let ttl = CacheManager.cacheTTL
        if age <= ttl {
            return String(format: "%.0f с (свежий, TTL %.0f с)", age, ttl)
        }
        return String(format: "%.0f с (устарел, TTL %.0f с)", age, ttl)
    }
}
