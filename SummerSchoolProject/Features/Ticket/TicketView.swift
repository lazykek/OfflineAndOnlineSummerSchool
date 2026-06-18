//
//  TicketView.swift
//  SummerSchoolProject
//

import SwiftUI

struct TicketView: View {
    @StateObject private var viewModel = TicketViewModel()

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Билет")
                .task { await viewModel.load() }
        }
    }

    @ViewBuilder
    private var content: some View {
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

    /// Показываем путь к JSON-файлу в Application Support — для лекции.
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

/// Баннер статуса синхронизации для offline-first билета.
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
