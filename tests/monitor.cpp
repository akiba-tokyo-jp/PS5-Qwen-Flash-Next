// SPDX-License-Identifier: MIT
// Host fixtures validate actual CPU rasterization and the complete tile mapping.
#include "monitor.h"
#include "tiled_frame.h"
#include "startup.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

static void check(bool value, const char * message) { if (!value) throw std::runtime_error(message); }
int main(int argc, char ** argv) {
    try {
        using namespace qwen_app;
        check(argc == 2, "Supply a host fixture output path");
        std::vector<bool> addresses(16u << 18, false);
        for (unsigned y = 0; y < MonitorRaster::height; ++y) for (unsigned x = 0; x < MonitorRaster::width; ++x) {
            const auto address = video_tiled_offset(x, y);
            check(address % 4 == 0 && address < (16u << 20), "Video tile address escaped its frame");
            check(!addresses[address / 4], "Video tile mapping aliases pixels"); addresses[address / 4] = true;
        }
        MonitorRaster raster;
        MonitorSnapshot value; value.state = "host renderer fixture"; value.message = "HOST RENDERER FIXTURE / NOT PS5 PERFORMANCE";
        value.epoch_ms = 1792627200000ULL; value.cpu_name = "CPU identity example"; value.gpu_name = "GPU identity example";
        value.cpu_threads = 16; value.request_id = "fixture"; value.generated_tokens = 1234;
        value.tokens_per_second = 12.34; value.elapsed_ms = 100000; value.ttft_ms = 1234;
        for (int i = 0; i < 60; ++i) { value.tokens_per_second = 10.0 + (i % 15) * 0.2; raster.draw(value); }
        check(raster.pixels().size() == MonitorRaster::width * MonitorRaster::height, "Raster frame size changed");
        std::ofstream file(argv[1], std::ios::binary);
        file << "P6\n" << MonitorRaster::width << ' ' << MonitorRaster::height << "\n255\n";
        for (auto pixel : raster.pixels()) { const char rgb[] = {char(pixel >> 16), char(pixel >> 8), char(pixel)}; file.write(rgb, 3); }
        file.close(); check(bool(file), "Host fixture write failed");
        std::string config = std::string(argv[1]) + ".json";
        { std::ofstream out(config); out << "{\"schema\":\"ps5-qwen-app-v1\",\"development_policy\":\"policy\",\"model_receipt\":\"model\",\"web_assets\":\"web\",\"mode\":\"monitor-validation\",\"port\":8086}"; }
        char app[] = "app"; char * args[] = {app, config.data()};
        const auto startup = read_startup(2, args);
        check(startup.monitor_validation && startup.native_display && startup.port == 8086, "Native startup configuration was not applied");
        { std::ofstream out(config); out << "{\"schema\":\"ps5-qwen-app-v1\",\"development_policy\":\"policy\",\"model_receipt\":\"model\",\"web_assets\":\"web\",\"mode\":\"display-validation\"}"; }
        check(read_startup(2, args).display_validation && !read_startup(2, args).monitor_validation, "Display-only validation was not isolated");
        { std::ofstream out(config); out << "{\"schema\":\"ps5-qwen-app-v1\",\"development_policy\":\"policy\",\"model_receipt\":\"model\",\"web_assets\":\"web\",\"port\":-1}"; }
        bool rejected = false; try { read_startup(2, args); } catch (const std::exception &) { rejected = true; }
        check(rejected, "Invalid native port was accepted");
        value.tokens_per_second = {}; value.cpu_name.clear(); value.gpu_name.clear(); raster.draw(value);
        std::cout << "All 2,073,600 tile addresses are unique/in bounds; native raster and startup checks passed\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
