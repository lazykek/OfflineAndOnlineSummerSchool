//
//  TicketView.swift
//  SummerSchoolProject
//

import SwiftUI

struct TicketView: View {
    @StateObject private var viewModel = TicketViewModel()

    @State private var isUnlocked = false
    @State private var authError: String? = nil
    @State private var isAuthenticating = false

    @Environment(\.scenePhase) private var scenePhase

    private let biometric = BiometricAuth.shared

    var body: some View {
        NavigationStack {
            Group {
                if isUnlocked {
                    unlockedContent
                } else {
                    biometricGateView
                }
            }
            .navigationTitle("Билет")
            .onChange(of: scenePhase) { _, newPhase in
                if newPhase == .background {
                    isUnlocked = false
                    authError = nil
                }
            }
        }
    }

    // MARK: - Biometric Gate

    private var biometricGateView: some View {
        VStack(spacing: 32) {
            Spacer()

            Image(systemName: biometric.biometryType.systemImage)
                .font(.system(size: 72))
                .foregroundStyle(.blue)
                .symbolEffect(.pulse)

            VStack(spacing: 8) {
                Text("Билет защищён")
                    .font(.title2.bold())
                Text("Подтвердите личность через \(biometric.biometryType.displayName),\nчтобы увидеть билет и QR-код")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            if let error = authError {
                HStack(spacing: 6) {
                    Image(systemName: "exclamationmark.triangle")
                    Text(error)
                }
                .font(.footnote)
                .foregroundStyle(.orange)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
            }

            Button {
                Task { await authenticate() }
            } label: {
                HStack(spacing: 8) {
                    if isAuthenticating {
                        ProgressView().scaleEffect(0.9)
                    } else {
                        Image(systemName: biometric.biometryType.systemImage)
                    }
                    Text("Разблокировать через \(biometric.biometryType.displayName)")
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .foregroundStyle(.white)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .disabled(isAuthenticating)
            .padding(.horizontal, 32)

            gateExplainerBadge

            Spacer()
        }
        .padding()
    }

    private var gateExplainerBadge: some View {
        VStack(alignment: .leading, spacing: 4) {
            Label("Данные уже на диске", systemImage: "info.circle")
                .font(.caption.bold())
                .foregroundStyle(.secondary)
            Text("FaceID не шифрует билет — данные лежат в Application Support.\nБиометрия решает лишь: ПОКАЗАТЬ их или нет.")
                .font(.caption2)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.leading)
        }
        .padding(10)
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: - Authentication

    private func authenticate() async {
        isAuthenticating = true
        authError = nil

        let reason = "Подтвердите личность, чтобы открыть билет"

        // Try biometrics-only first.
        let result = await biometric.authenticate(reason: reason)

        switch result {
        case .success:
            isUnlocked = true
            await viewModel.load()

        case .failure(let error):
            switch error {
            case .notEnrolled, .lockout, .unavailable:
                let fallbackResult = await biometric.authenticate(
                    reason: reason,
                    allowPasscodeFallback: true
                )
                switch fallbackResult {
                case .success:
                    isUnlocked = true
                    await viewModel.load()
                case .failure(.canceled):
                    authError = nil
                case .failure(let fallbackErr):
                    authError = fallbackErr.errorDescription
                }
            case .canceled:
                authError = nil
            default:
                authError = error.errorDescription
            }
        }

        isAuthenticating = false
    }

    // MARK: - Unlocked Content

    @ViewBuilder
    private var unlockedContent: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingView()
        case .loaded(let ticket):
            VStack(spacing: 0) {
                SyncStatusBadge(status: viewModel.syncStatus)
                ticketCard(ticket)
            }
        case .failed(let error):
            ErrorStateView(error: error) {
                Task { await viewModel.load() }
            }
        }
    }

    private func ticketCard(_ ticket: Ticket) -> some View {
        ScrollView {
            VStack(spacing: 20) {
                if let qr = QRCodeGenerator.image(from: ticket.qrPayload) {
                    Image(uiImage: qr)
                        .interpolation(.none)
                        .resizable()
                        .scaledToFit()
                        .frame(width: 220, height: 220)
                } else {
                    Text("Не удалось построить QR-код")
                        .foregroundStyle(.secondary)
                }

                VStack(spacing: 8) {
                    Text(ticket.passengerName)
                        .font(.title2.bold())
                    HStack(spacing: 24) {
                        info("Рейс", ticket.flightNumber)
                        info("Место", ticket.seat)
                        info("Выход", ticket.gate)
                    }
                }

                debugFilePath
            }
            .padding()
        }
    }

    private func info(_ title: String, _ value: String) -> some View {
        VStack(spacing: 2) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.headline)
        }
    }

    private var debugFilePath: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("📁 Локальный стор (Application Support)")
                .font(.caption.bold())
                .foregroundStyle(.secondary)
            Text(TicketRepository.shared.localFilePath)
                .font(.system(.caption2, design: .monospaced))
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.leading)
        }
        .padding(10)
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .padding(.top, 8)
    }
}

// MARK: - SyncStatusBadge

struct SyncStatusBadge: View {
    let status: TicketSyncStatus

    var body: some View {
        switch status {
        case .syncing:
            HStack(spacing: 6) {
                ProgressView().scaleEffect(0.7)
                Text("Синхронизация…")
            }
            .font(.footnote)
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
            .background(.thinMaterial)

        case .synced(let at):
            HStack(spacing: 6) {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                Text("Синхронизировано \(at.formatted(date: .omitted, time: .shortened))")
            }
            .font(.footnote)
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
            .background(Color.green.opacity(0.08))

        case .offline:
            HStack(spacing: 6) {
                Image(systemName: "wifi.slash")
                Text("Офлайн — последний сохранённый билет")
            }
            .font(.footnote)
            .foregroundStyle(.orange)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
            .background(Color.orange.opacity(0.12))
        }
    }
}
