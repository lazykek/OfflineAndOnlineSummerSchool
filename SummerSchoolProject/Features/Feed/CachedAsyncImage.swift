//
//  CachedAsyncImage.swift
//  SummerSchoolProject
//

import SwiftUI

struct CachedAsyncImage: View {
    let url: URL?

    @State private var image: UIImage?
    @State private var failed = false

    var body: some View {
        Group {
            if let image {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
            } else {
                placeholder
            }
        }
        .task(id: url) { await load() }
    }

    private var placeholder: some View {
        ZStack {
            Color(.secondarySystemBackground)
            Image(systemName: failed ? "wifi.slash" : "photo")
                .foregroundStyle(.secondary)
        }
    }

    private func load() async {
        guard let url else { return }
        failed = false
        do {
            image = try await ImageLoader.shared.image(for: url)
        } catch {
            failed = true
        }
    }
}
