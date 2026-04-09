import L from "leaflet";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import type { MapCenterRow, MapOrderRow } from "../api/client";

type SimulationMapProps = {
    orderRows: MapOrderRow[];
    centerRows: MapCenterRow[];
};

export function SimulationMap({ orderRows, centerRows }: SimulationMapProps) {
    const orderFeatures: GeoJSON.FeatureCollection<GeoJSON.Point> = {
        type: "FeatureCollection",
        features: orderRows.map((row) => ({
            type: "Feature",
            geometry: {
                type: "Point",
                coordinates: [row.customer_lon, row.customer_lat],
            },
            properties: {
                ...row,
            },
        })),
    };

    const centerFeatures: GeoJSON.FeatureCollection<GeoJSON.Point> = {
        type: "FeatureCollection",
        features: centerRows.map((row) => ({
            type: "Feature",
            geometry: {
                type: "Point",
                coordinates: [row.center_lon, row.center_lat],
            },
            properties: {
                ...row,
            },
        })),
    };

    return (
        <div className="map-panel">
            <MapContainer center={[36.2, 138.2]} zoom={5} scrollWheelZoom preferCanvas className="leaflet-map">
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <GeoJSON
                    data={orderFeatures}
                    pointToLayer={(feature, latlng) => {
                        const properties = feature.properties as MapOrderRow;

                        return L.circleMarker(latlng, {
                            radius: getOrderRadius(properties.weight_kg),
                            fillColor: getOrderColor(properties),
                            color: properties.is_unassigned ? "#7f1d1d" : "rgba(11, 26, 43, 0.15)",
                            weight: properties.is_unassigned ? 1.3 : 0.8,
                            opacity: 1,
                            fillOpacity: properties.is_unassigned ? 0.92 : 0.56,
                        });
                    }}
                    onEachFeature={(feature, layer) => {
                        const properties = feature.properties as MapOrderRow;
                        layer.bindPopup(
                            [
                                `<strong>注文ID:</strong> ${properties.order_id}`,
                                `<strong>担当拠点:</strong> ${properties.assigned_center_name}`,
                                `<strong>割当状態:</strong> ${properties.assignment_status}`,
                                `<strong>重量:</strong> ${properties.weight_kg.toFixed(1)} kg`,
                                `<strong>配送コスト:</strong> ¥${Math.round(properties.simulated_cost).toLocaleString("ja-JP")}`,
                            ].join("<br>"),
                        );
                    }}
                />
                <GeoJSON
                    data={centerFeatures}
                    pointToLayer={(feature, latlng) => {
                        const properties = feature.properties as MapCenterRow;

                        return L.circleMarker(latlng, {
                            radius: Math.max(8, Math.min(18, 8 + properties.staffing_level * 0.15)),
                            fillColor: "#173252",
                            color: "#ffffff",
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.94,
                        });
                    }}
                    onEachFeature={(feature, layer) => {
                        const properties = feature.properties as MapCenterRow;
                        layer.bindPopup(
                            [
                                `<strong>拠点:</strong> ${properties.center_name}`,
                                `<strong>人員数:</strong> ${properties.staffing_level.toLocaleString("ja-JP")} 人`,
                                `<strong>固定費:</strong> ¥${Math.round(properties.fixed_cost).toLocaleString("ja-JP")}`,
                            ].join("<br>"),
                        );
                    }}
                />
            </MapContainer>
        </div>
    );
}

function getOrderRadius(weightKg: number): number {
    return Math.max(2, Math.min(8, 2 + weightKg / 8));
}

function getOrderColor(row: MapOrderRow): string {
    return `rgb(${row.color_r}, ${row.color_g}, ${row.color_b})`;
}