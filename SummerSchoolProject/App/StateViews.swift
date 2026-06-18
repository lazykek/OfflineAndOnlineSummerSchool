//
//  StateViews.swift
//  SummerSchoolProject
//

import SwiftUI

struct LoadingView: View {
    var body: some View {
        ProgressView("Загрузка…")
            .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct ErrorStateView: View {
    let error: Error
    let retry: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "wifi.slash")
                .font(.system(size: 44))
                .foregroundStyle(.secondary)
            Text(error.localizedDescription)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
            Button("Повторить", action: retry)
                .buttonStyle(.borderedProminent)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Cache badges

struct CacheBadge: View {
    let dataSource: DataSource

    var body: some View {
        switch dataSource {
        case .network:
            EmptyView()
        case .staleCache(let age):
            StaleBadge(age: age)
        case .offlineCache:
            OfflineBadge()
        }
    }
}

struct StaleBadge: View {
    let age: TimeInterval

    private var ageText: String {
        if age == .infinity { return "" }
        let mins = Int(age) / 60
        let secs = Int(age) % 60
        if mins > 0 { return " · \(mins) мин \(secs) с назад" }
        return " · \(secs) с назад"
    }

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "arrow.triangle.2.circlepath")
            Text("Данные могли устареть · обновляем…\(ageText)")
        }
        .font(.footnote)
        .foregroundStyle(.orange)
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(Color.orange.opacity(0.12))
    }
}

struct OfflineBadge: View {
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "wifi.slash")
            Text("Оффлайн — сохранённые данные")
        }
        .font(.footnote)
        .foregroundStyle(.secondary)
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(.thinMaterial)
    }
}
