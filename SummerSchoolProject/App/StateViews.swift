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
