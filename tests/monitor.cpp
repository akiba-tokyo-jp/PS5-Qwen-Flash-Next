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
        const std::int64_t console_epoch = 1792649360000LL;
        const auto steady = MonitorClock::Steady::time_point(std::chrono::seconds(100));
        MonitorClock clock;
        clock.initialize(ClockCalibration{console_epoch, console_epoch - 677000, 1500}, console_epoch + 2000, steady);
        check(clock.calibrated() && clock.now(steady) == console_epoch - 675000,
              "Observed console offset was not corrected locally");
        check(clock.now(steady + std::chrono::seconds(3)) == console_epoch - 672000,
              "Calibrated UTC must advance with the monotonic clock");
        auto reject_clock = [&](ClockCalibration calibration, std::int64_t now) {
            MonitorClock invalid; bool refused = false;
            try { invalid.initialize(calibration, now, steady); } catch (const std::exception &) { refused = true; }
            check(refused, "Invalid or stale clock calibration was admitted");
        };
        reject_clock({console_epoch, console_epoch, 5001}, console_epoch);
        reject_clock({console_epoch, console_epoch, -1}, console_epoch);
        reject_clock({console_epoch, console_epoch, 1000}, console_epoch + 900001);
        reject_clock({console_epoch, console_epoch, 1000}, console_epoch - 1001);
        reject_clock({console_epoch, console_epoch - 86400001, 1000}, console_epoch);
        reject_clock({0, console_epoch, 1000}, console_epoch);
        MonitorClock uncalibrated; uncalibrated.initialize({}, console_epoch, steady);
        check(!uncalibrated.calibrated() && !uncalibrated.initial_uncertainty_ms() &&
              uncalibrated.now(steady + std::chrono::seconds(1)) == console_epoch + 1000,
              "Uncalibrated clock source must remain explicit");
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
        const std::string base = "{\"schema\":\"ps5-qwen-app-v1\",\"development_policy\":\"policy\",\"model_receipt\":\"model\",\"web_assets\":\"web\",\"clock_calibration\":";
        { std::ofstream out(config); out << base << "{\"schema\":\"ps5-qwen-clock-offset-v1\",\"console_epoch_ms\":1792649360000,\"utc_epoch_ms\":1792648683000,\"uncertainty_ms\":1500}}"; }
        check(read_startup(2, args).clock_calibration->utc_epoch_ms == console_epoch - 677000,
              "Clock calibration must retain exact epoch integers");
        for (const char * bad : {"true", "1.5", "-1", "18446744073709551615", "\"1792649360000\""}) {
            { std::ofstream out(config); out << base << "{\"schema\":\"ps5-qwen-clock-offset-v1\",\"console_epoch_ms\":" << bad << ",\"utc_epoch_ms\":1792648683000,\"uncertainty_ms\":1500}}"; }
            bool refused = false; try { read_startup(2, args); } catch (const std::exception &) { refused = true; }
            check(refused, "Malformed clock epoch was accepted");
        }
        { std::ofstream out(config); out << "{\"schema\":\"ps5-qwen-app-v1\",\"development_policy\":\"policy\",\"model_receipt\":\"model\",\"web_assets\":\"web\",\"mode\":\"display-validation\"}"; }
        check(read_startup(2, args).display_validation && !read_startup(2, args).monitor_validation, "Display-only validation was not isolated");
        { std::ofstream out(config); out << "{\"schema\":\"ps5-qwen-app-v1\",\"development_policy\":\"policy\",\"model_receipt\":\"model\",\"web_assets\":\"web\",\"mode\":\"model-validation\",\"native_display\":false}"; }
        const auto model_startup = read_startup(2, args);
        check(model_startup.model_validation && !model_startup.monitor_validation &&
              !model_startup.runtime_validation && !model_startup.native_display, "Model CPU validation was not isolated");
        { std::ofstream out(config); out << "{\"schema\":\"ps5-qwen-app-v1\",\"development_policy\":\"policy\",\"model_receipt\":\"model\",\"web_assets\":\"web\",\"mode\":\"operator-validation\",\"native_display\":false,\"weight_fixture\":\"/app0/qwen-runtime/original-weight-fixture.bf16\"}"; }
        const auto operation_startup = read_startup(2, args);
        check(operation_startup.operator_validation && !operation_startup.model_validation &&
              !operation_startup.monitor_validation && !operation_startup.native_display,
              "Original-weight diagnostic mode was not isolated");
        { std::ofstream out(config); out << "{\"schema\":\"ps5-qwen-app-v1\",\"development_policy\":\"policy\",\"model_receipt\":\"model\",\"web_assets\":\"web\",\"mode\":\"operator-validation\",\"weight_fixture\":\"/data/outside-fixture.bf16\"}"; }
        bool invalid_fixture=false;try{read_startup(2,args);}catch(const std::exception &){invalid_fixture=true;}
        check(invalid_fixture,"An unbound original-weight fixture path was admitted");
        { std::ofstream out(config); out << "{\"schema\":\"ps5-qwen-app-v1\",\"development_policy\":\"policy\",\"model_receipt\":\"model\",\"web_assets\":\"web\",\"port\":-1}"; }
        bool rejected = false; try { read_startup(2, args); } catch (const std::exception &) { rejected = true; }
        check(rejected, "Invalid native port was accepted");
        value.tokens_per_second = {}; value.cpu_name.clear(); value.gpu_name.clear(); raster.draw(value);
        std::cout << "All 2,073,600 tile addresses are unique/in bounds; native raster and startup checks passed\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
