import L from "leaflet";
import { memo, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMapEvents } from "react-leaflet";
import type { MapCenterRow, MapOrderRow } from "../api/client";

type SimulationMapProps = {
    orderRows: MapOrderRow[];
    centerRows: MapCenterRow[];
};

export const SimulationMap = memo(function SimulationMap({ orderRows, centerRows }: SimulationMapProps) {
    const [zoomLevel, setZoomLevel] = useState<number>(5);
    const orderFeatures = useMemo<GeoJSON.FeatureCollection<GeoJSON.Point>>(
        () => ({
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
        }),
        [orderRows],
    );

    const centerFeatures = useMemo<GeoJSON.FeatureCollection<GeoJSON.Point>>(
        () => ({
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
        }),
        [centerRows],
    );

    return (
        <div className="map-panel">
            <MapContainer center={[36.2, 138.2]} zoom={5} scrollWheelZoom preferCanvas className="leaflet-map">
                <MapZoomTracker onZoomChange={setZoomLevel} />
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <GeoJSON
                    data={orderFeatures}
                    pointToLayer={(feature, latlng) => {
                        const properties = feature.properties as MapOrderRow;

                        return L.circleMarker(latlng, {
                            radius: getOrderRadius(properties.weight_kg, zoomLevel),
                            fillColor: getOrderColor(properties),
                            color: properties.is_unassigned ? "#7f1d1d" : "rgba(11, 26, 43, 0.12)",
                            weight: properties.is_unassigned ? 1.6 : 0.9,
                            opacity: 1,
                            fillOpacity: properties.is_unassigned ? 0.98 : 0.72,
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
                            radius: Math.max(9, Math.min(19, 9 + properties.staffing_level * 0.12)),
                            fillColor: "rgba(18, 122, 142, 0.55)",
                            color: "rgba(7, 59, 76, 0.95)",
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.78,
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
});

function MapZoomTracker({ onZoomChange }: { onZoomChange: (zoom: number) => void }) {
    useMapEvents({
        zoomend(event) {
            onZoomChange(event.target.getZoom());
        },
    });

    return null;
}

function getOrderRadius(weightKg: number, zoomLevel: number): number {
    const weightRadius = Math.max(4.5, Math.min(10.5, 4.5 + weightKg / 18));
    const zoomBonus = Math.max(0, zoomLevel - 5) * 0.35;
    return Math.min(13, weightRadius + zoomBonus);
}

function getOrderColor(row: MapOrderRow): string {
    return `rgb(${row.color_r}, ${row.color_g}, ${row.color_b})`;
}